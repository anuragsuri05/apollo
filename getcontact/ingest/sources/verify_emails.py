"""Bulk SMTP verification of guessed / mx_valid emails (what Apollo's verification pipeline does before
sending). True → verified, False → tries the other common patterns, None (catch-all, greylisted) → unchanged.

    python -m ingest.run verify_emails --limit 2000 --workers 8 --seniority c_suite,vp
Note: many corporate mail hosts reject or greylist probes from residential IPs; run from a server with
reverse DNS for best results. Never more than a few per second per domain.
"""
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.email_engine import guess_email
from app.models import Organization, Person


def add_args(p):
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--seniority", help="comma list filter")
    p.add_argument("--status", default="guessed,mx_valid")


def run(ing, args):
    q = ing.db.query(Person).join(Organization, Person.organization_id == Organization.id).filter(
        Person.email.isnot(None), Person.email_status.in_(args.status.split(",")), Organization.domain.isnot(None))
    if args.seniority:
        q = q.filter(Person.seniority.in_(args.seniority.split(",")))
    rows = q.limit(args.limit or 500).all()
    ing.log(f"verifying {len(rows)} addresses")
    last_hit = defaultdict(float)

    def work(per):
        dom = per.organization.domain
        wait = 1.0 - (time.time() - last_hit[dom])
        if wait > 0:
            time.sleep(wait)
        last_hit[dom] = time.time()
        email, status, conf = guess_email(ing.db, per.first_name, per.last_name, dom, verify=True)
        return per, email, status

    ok = bad = unk = 0
    with ThreadPoolExecutor(args.workers) as ex:
        for i, (per, email, status) in enumerate(ex.map(work, rows)):
            if status == "verified":
                per.email, per.email_status, per.last_verified_at = email, "verified", datetime.utcnow()
                ok += 1
            elif status == "invalid":
                per.email_status = "invalid"
                bad += 1
            else:
                unk += 1
            ing.run.rows_in += 1
            if i % 100 == 0:
                ing.commit()
                ing.log(f"verified={ok} invalid={bad} inconclusive={unk}")
    ing.commit()
    ing.log(f"done verified={ok} invalid={bad} inconclusive={unk}")
