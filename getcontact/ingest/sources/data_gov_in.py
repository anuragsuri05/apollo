"""India: Ministry of Corporate Affairs company master data published on data.gov.in (free API key).

1. Register at https://data.gov.in → My Account → API key.
2. Find a "Company Master Data" resource (one per state), copy its resource id from the URL.
    DATA_GOV_IN_API_KEY=... python -m ingest.run data_gov_in --resource <resource-id> --limit 50000
"""
import time

from app.config import DATA_GOV_IN_API_KEY

API = "https://api.data.gov.in/resource/{rid}"


def add_args(p):
    p.add_argument("--resource", action="append", required=True, help="data.gov.in resource id (repeatable)")
    p.add_argument("--page", type=int, default=1000)


def _pick(row, *cands):
    low = {k.lower(): v for k, v in row.items()}
    for c in cands:
        for k, v in low.items():
            if c in k and v not in (None, "", "NA"):
                return v
    return None


def run(ing, args):
    if not DATA_GOV_IN_API_KEY:
        raise SystemExit("set DATA_GOV_IN_API_KEY")
    total = 0
    for rid in args.resource:
        offset = 0
        while True:
            r = ing.get(API.format(rid=rid), params={"api-key": DATA_GOV_IN_API_KEY, "format": "json", "limit": args.page, "offset": offset})
            if r.status_code != 200:
                ing.log(f"HTTP {r.status_code}: {r.text[:200]}")
                break
            recs = r.json().get("records") or []
            if not recs:
                break
            for row in recs:
                cin = _pick(row, "corporate_identification_number", "cin")
                name = _pick(row, "company_name", "name")
                if not cin or not name:
                    continue
                reg = _pick(row, "date_of_registration", "registration_date") or ""
                ing.upsert_org(name.title(), cin, company_number=cin, country="IN", state=_pick(row, "registered_state", "state"),
                               industry=_pick(row, "principal_business_activity", "industrial_class", "activity"),
                               status=(_pick(row, "company_status", "status") or "").lower() or None,
                               address=_pick(row, "registered_office_address", "address"),
                               founded_year=int(reg[-4:]) if reg[-4:].isdigit() else None,
                               source_url="https://www.mca.gov.in/")
                total += 1
                if args.limit and total >= args.limit:
                    ing.commit()
                    return
            ing.commit()
            ing.progress()
            offset += args.page
            time.sleep(0.5)
