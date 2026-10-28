"""OpenCorporates (free API token for non-commercial use; 200M+ companies, officers for many jurisdictions).

    OPENCORPORATES_TOKEN=... python -m ingest.run opencorporates --query "software" --jurisdiction in --limit 2000
    OPENCORPORATES_TOKEN=... python -m ingest.run opencorporates --officers --query "chief executive" --jurisdiction gb
"""
import time

from app.config import OPENCORPORATES_TOKEN

COMPANIES = "https://api.opencorporates.com/v0.4/companies/search"
OFFICERS = "https://api.opencorporates.com/v0.4/officers/search"


def add_args(p):
    p.add_argument("--query", required=True, help="company-name (or officer-position with --officers) search term")
    p.add_argument("--jurisdiction", help="e.g. in, gb, us_de, us_ca")
    p.add_argument("--officers", action="store_true", help="search officers instead of companies")
    p.add_argument("--per-page", type=int, default=100)


def run(ing, args):
    if not OPENCORPORATES_TOKEN:
        raise SystemExit("set OPENCORPORATES_TOKEN")
    page, total = 1, 0
    while True:
        params = {"q": args.query, "api_token": OPENCORPORATES_TOKEN, "per_page": args.per_page, "page": page}
        if args.jurisdiction:
            params["jurisdiction_code"] = args.jurisdiction
        r = ing.get(OFFICERS if args.officers else COMPANIES, params=params)
        if r.status_code != 200:
            ing.log(f"HTTP {r.status_code}: {r.text[:200]}")
            break
        res = r.json().get("results") or {}
        items = res.get("officers" if args.officers else "companies") or []
        if not items:
            break
        for it in items:
            if args.officers:
                of = it["officer"]
                c = of.get("company") or {}
                org = ing.upsert_org(c.get("name"), f"{c.get('jurisdiction_code')}/{c.get('company_number')}", company_number=c.get("company_number"),
                                     country=(c.get("jurisdiction_code") or "")[:2].upper() or None, source_url="https://opencorporates.com" + (c.get("opencorporates_url") or "")) if c.get("name") else None
                if of.get("end_date"):
                    continue
                ing.upsert_person(of.get("name"), str(of.get("id")), org, title=(of.get("position") or "").title() or None,
                                  source_url=of.get("opencorporates_url"))
            else:
                c = it["company"]
                addr = c.get("registered_address") or {}
                ing.upsert_org(c.get("name"), f"{c.get('jurisdiction_code')}/{c.get('company_number')}", company_number=c.get("company_number"),
                               country=(c.get("jurisdiction_code") or "")[:2].upper() or None, status=(c.get("current_status") or "").lower() or None,
                               city=addr.get("locality"), state=addr.get("region"), postal_code=addr.get("postal_code"),
                               founded_year=int(c["incorporation_date"][:4]) if c.get("incorporation_date") else None,
                               source_url=c.get("opencorporates_url"))
            total += 1
            if args.limit and total >= args.limit:
                ing.commit()
                return
        ing.commit()
        ing.progress()
        if page >= int(res.get("total_pages") or 1):
            break
        page += 1
        time.sleep(1)
