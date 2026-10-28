"""Hunter.io domain search with your own (free: 25 searches/mo) key → verified emails, names, titles and the
domain's email pattern, which the email engine then reuses for every other person at that company.

    HUNTER_API_KEY=... python -m ingest.run hunter --domains stripe.com,zomato.com
    HUNTER_API_KEY=... python -m ingest.run hunter --from-db 20     # 20 orgs with domain but no known pattern
"""
import time

from app.config import HUNTER_API_KEY
from app.models import EmailPattern, Organization

API = "https://api.hunter.io/v2/domain-search"
STATUS = {"valid": "verified", "accept_all": "mx_valid", "unknown": "guessed", "invalid": "invalid"}


def add_args(p):
    p.add_argument("--domains", help="comma-separated domains")
    p.add_argument("--from-db", type=int, default=0, help="pick N organizations from the DB that have a domain but no email pattern")


def run(ing, args):
    if not HUNTER_API_KEY:
        raise SystemExit("set HUNTER_API_KEY")
    domains = [d.strip().lower() for d in (args.domains or "").split(",") if d.strip()]
    if args.from_db:
        q = ing.db.query(Organization).filter(Organization.domain.isnot(None), Organization.email_pattern.is_(None)).order_by(Organization.employee_count.desc().nullslast()).limit(args.from_db)
        domains += [o.domain for o in q]
    for d in domains:
        r = ing.get(API, params={"domain": d, "api_key": HUNTER_API_KEY, "limit": 100})
        if r.status_code != 200:
            ing.log(f"{d}: HTTP {r.status_code} {r.text[:120]}")
            if r.status_code in (401, 429):
                break
            continue
        data = r.json().get("data") or {}
        org = ing.upsert_org(data.get("organization") or d, d, source="hunter", domain=d, industry=data.get("industry"),
                             country=data.get("country"), state=data.get("state"), city=data.get("city"),
                             linkedin_url=data.get("linkedin"), description=data.get("description"))
        if data.get("pattern") and org:
            pat = data["pattern"]
            org.email_pattern = pat
            row = ing.db.get(EmailPattern, d)
            if row:
                row.pattern, row.confidence = pat, max(row.confidence, 0.9)
            else:
                ing.db.add(EmailPattern(domain=d, pattern=pat, confidence=0.9, samples=len(data.get("emails") or [])))
        for e in data.get("emails") or []:
            full = f"{e.get('first_name') or ''} {e.get('last_name') or ''}".strip()
            if not full:
                continue
            st = STATUS.get(((e.get("verification") or {}).get("status")) or "", "guessed")
            if st == "guessed" and (e.get("confidence") or 0) >= 90:
                st = "mx_valid"
            ing.upsert_person(full, e["value"], org, first_name=e.get("first_name"), last_name=e.get("last_name"), title=e.get("position"),
                              email=e["value"], email_status=st, linkedin_url=e.get("linkedin"), phone=e.get("phone_number"),
                              source_url=(e.get("sources") or [{}])[0].get("uri"))
        ing.commit()
        ing.progress()
        time.sleep(1)
