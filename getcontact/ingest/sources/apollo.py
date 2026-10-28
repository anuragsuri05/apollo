"""Apollo.io enrichment with your own API key (free plan works). Enriches people already in the DB who
lack an email, one person per call (1 Apollo credit per email found). Respects Apollo's per-minute limit.

NOTE: Apollo's terms forbid bulk-replicating their database; this connector only enriches records you
already hold, which is the intended use of people/match.

    APOLLO_API_KEY=... python -m ingest.run apollo --limit 100 --seniority c_suite,vp
"""
import time

from app.config import APOLLO_API_KEY
from app.models import Organization, Person

MATCH = "https://api.apollo.io/api/v1/people/match"


def add_args(p):
    p.add_argument("--seniority", help="comma list, e.g. c_suite,vp,director")
    p.add_argument("--country", help="restrict to organizations in ISO-2 country")
    p.add_argument("--reveal-phone", action="store_true", help="costs 8 Apollo credits each")


def run(ing, args):
    if not APOLLO_API_KEY:
        raise SystemExit("set APOLLO_API_KEY")
    q = ing.db.query(Person).join(Organization, Person.organization_id == Organization.id).filter(Person.email.is_(None), Organization.domain.isnot(None))
    if args.seniority:
        q = q.filter(Person.seniority.in_(args.seniority.split(",")))
    if args.country:
        q = q.filter(Organization.country == args.country)
    rows = q.limit(args.limit or 50).all()
    ing.log(f"enriching {len(rows)} people via Apollo")
    for i, per in enumerate(rows):
        params = {"first_name": per.first_name, "last_name": per.last_name, "domain": per.organization.domain,
                  "reveal_personal_emails": "false", "reveal_phone_number": "false"}
        r = ing.http.post(MATCH, params=params, headers={"x-api-key": APOLLO_API_KEY, "Content-Type": "application/json"})
        if r.status_code == 429:
            wait = int(r.headers.get("retry-after", 60))
            ing.log(f"rate limited; sleeping {wait}s")
            time.sleep(wait)
            continue
        if r.status_code != 200:
            ing.log(f"HTTP {r.status_code}: {r.text[:120]}")
            if r.status_code in (401, 403):
                break
            continue
        p = (r.json() or {}).get("person") or {}
        if p.get("email"):
            st = "verified" if p.get("email_status") == "verified" else "mx_valid"
            ing.upsert_person(per.full_name, per.source_id, per.organization, source=per.source, email=p["email"], email_status=st,
                              title=p.get("title"), linkedin_url=p.get("linkedin_url"), city=p.get("city"), state=p.get("state"))
        if i % 20 == 0:
            ing.commit()
            ing.progress()
        time.sleep(0.3)
