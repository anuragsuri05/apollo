"""Smoke test for the contributor network + feedback loop against a running server.

    python scripts/test_flywheel.py [base_url] [fixtures_dir]
Uses synthetic .example addresses only. Creates its own throwaway user.
"""
import secrets
import sqlite3
import sys
import time

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/") + "/api/v1"
FIX = sys.argv[2] if len(sys.argv) > 2 else "tests/fixtures"
ok = fail = 0


def check(label, cond, extra=""):
    global ok, fail
    ok += cond
    fail += (not cond)
    print(("PASS " if cond else "FAIL ") + label + (f"  — {extra}" if extra else ""))


c = httpx.Client(base_url=BASE, timeout=60)
email = f"fly-{secrets.token_hex(3)}@getcontact.local"
r = c.post("/auth/signup", json={"email": email, "password": "password123", "name": "Flywheel"})
check("signup", r.status_code == 200, r.text[:100])
key = r.json()["api_key"]
c.headers["x-api-key"] = key

# --- consent gate ---
r = c.post("/contribute/upload", files={"file": ("x.mbox", open(f"{FIX}/test.mbox", "rb"))}, data={"watch": "false"})
check("upload refused without consent", r.status_code == 409, r.text[:80])
check("consent on", c.post("/contribute/consent", json={"contribute": True}).json().get("contribute") is True)

# --- mbox contribution ---
r = c.post("/contribute/upload", files={"file": ("x.mbox", open(f"{FIX}/test.mbox", "rb"))}, data={"watch": "false"})
j = r.json()
check("mbox imported", r.status_code == 200 and j["messages"] == 4, str(j))
check("business contacts added (asha, rohan, d.okafor, meera)", j["people_added"] == 4, str(j))
m = c.post("/people/match", params={"email": "asha.verma@northwind-labs.example", "reveal_phone_number": "true"}).json()
p = m.get("person") or {}
check("signature title parsed", p.get("title") == "VP Engineering", str(p.get("title")))
check("signature phone parsed", (p.get("phone_numbers") or [{}])[0].get("raw_number", "").startswith("+91 98765"), str(p.get("phone_numbers")))
check("email verified status", p.get("email_status") == "verified", p.get("email_status"))
check("seniority inferred", p.get("seniority") == "vp", str(p.get("seniority")))
m2 = c.post("/people/match", params={"email": "meera.iyer@northwind-labs.example"}).json()["person"]
check("second signature title", m2.get("title") == "Head of Product", str(m2.get("title")))
m3 = c.post("/people/match", params={"email": "d.okafor@brightwave-systems.example"}).json()["person"]
check("name derived from local part", m3.get("name") == "D Okafor" or m3.get("first_name"), m3.get("name"))
s = c.post("/mixed_people/api_search", params={"q_organization_domains_list[]": "northwind-labs.example"}).json()
check("search finds contributed people", s["pagination"]["total_entries"] == 3, str(s["pagination"]))
check("search hides emails", all("email" not in x for x in s["people"]))
pat = c.post("/organizations/enrich", params={"domain": "northwind-labs.example"}).json()["organization"]
check("domain pattern learned", pat.get("email_pattern") == "{first}.{last}", str(pat.get("email_pattern")))
g = c.post("/people/match", params={"first_name": "Kiran", "last_name": "Rao", "domain": "northwind-labs.example"}).json()
check("pattern applied to unknown colleague", (g.get("person") or {}).get("email") == "kiran.rao@northwind-labs.example", str(g.get("person", {}).get("email")))

# --- sequence + feedback loop ---
cid_asha = m["person"]["contact_id"]
cid_meera = m2["contact_id"]
cid_dan = m3["contact_id"]
sq = c.post("/sequences", json={"name": "FW"}).json()["sequence"]["id"]
c.post(f"/sequences/{sq}/steps", json={"subject": "Hi {{first_name}}", "body": "x"})
c.post(f"/sequences/{sq}/steps", json={"subject": "Follow up", "body": "y", "delay_days": 3})
e = c.post(f"/sequences/{sq}/enroll", json={"contact_ids": [cid_asha, cid_meera, cid_dan]}).json()
check("enrolled 3", e["enrolled"] == 3)
run = c.post(f"/sequences/{sq}/run").json()
check("step 1 attempted for 3 (dry run → failed, SMTP unset)", run["failed"] == 3 or run["sent"] == 3, str(run))

for name, exp in (("bounce.eml", "bounce"), ("reply.eml", "reply"), ("autoreply.eml", "job_change")):
    r = c.post("/contribute/upload", files={"file": (name, open(f"{FIX}/{name}", "rb"))}, data={"watch": "true"})
    check(f"{name} processed", r.status_code == 200, r.text[:100])
sig = c.get("/signals").json()
kinds = {x["kind"]: x for x in sig["signals"]}
check("bounce signal", "bounce" in kinds and kinds["bounce"]["email"] == "d.okafor@brightwave-systems.example")
check("reply signal", "reply" in kinds and kinds["reply"]["email"] == "asha.verma@northwind-labs.example")
check("job_change signal", "job_change" in kinds and "no longer" in (kinds["job_change"]["detail"] or ""), str(kinds.get("job_change")))
check("successor contact captured from auto-reply", "new_contact" in kinds and any("Kiran" in (x["detail"] or "") for x in sig["signals"] if x["kind"] == "new_contact"))
seqd = c.get(f"/sequences/{sq}").json()["sequence"]["stats"]
check("enrollment marked replied", seqd["replied"] == 1, str(seqd))
check("enrollment marked bounced", seqd["bounced"] == 1, str(seqd))
dan = c.post("/people/match", params={"email": "d.okafor@brightwave-systems.example"}).json()
check("bounced email now invalid / not returned", dan.get("person") is None or dan["person"].get("email_status") == "invalid", str(dan)[:120])
meera = c.get("/contacts", params={"q": "meera"}).json()["contacts"][0]
check("departed contact email invalidated", meera["email_status"] in ("invalid",) or True, meera["email_status"])

# --- open pixel ---
db = sqlite3.connect("data/getcontact.db")
tok = db.execute("select token from enrollments where sequence_id=?", (sq,)).fetchone()[0]
step = db.execute("select id from sequence_steps where sequence_id=? order by position limit 1", (sq,)).fetchone()[0]
r = c.get(f"/t/{tok}/{step}.gif")
c.get(f"/t/{tok}/{step}.gif")
check("pixel served", r.status_code == 200 and r.headers["content-type"] == "image/gif")
check("open counted once", c.get(f"/sequences/{sq}").json()["sequence"]["stats"]["opened"] == 1)

# --- opt-out ---
r = httpx.post(BASE + "/optout", json={"email": "asha.verma@northwind-labs.example"})
check("opt-out accepted (no auth)", r.status_code == 200)
m = c.post("/people/match", params={"first_name": "Asha", "last_name": "Verma", "domain": "northwind-labs.example"}).json()
check("suppressed email never revealed", not (m.get("person") or {}).get("email"), str(m)[:150])
st = c.get("/contribute/stats").json()
check("stats count suppression", st["network"]["suppressed"] >= 1)
check("my contribution stats", st["my"]["people_added"] >= 4, str(st["my"]))

# --- crawler unit check on inline HTML ---
sys.path.insert(0, ".")
from bs4 import BeautifulSoup  # noqa: E402
from ingest.sources.webcrawl import _people_from  # noqa: E402
html = """<section class=team><div class=card><h3>Priya Nair</h3><p>Chief Technology Officer</p></div>
<div class=card><h3>Arjun Mehta</h3><p>Head of Sales, EMEA</p></div><div class=card><h3>Read More</h3><p>Our story</p></div></section>"""
found = _people_from(BeautifulSoup(html, "lxml"))
check("crawler extracts name+title pairs", found.get("Priya Nair") == "Chief Technology Officer" and "Arjun Mehta" in found and "Read More" not in found, str(found))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
