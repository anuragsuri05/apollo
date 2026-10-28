"""SEC EDGAR: all SEC-registered tickers, then per-filer details (SIC, website, address, phone).

Free, no key. SEC asks for a descriptive User-Agent and <=10 req/s.
"""
import time

TICKERS = "https://www.sec.gov/files/company_tickers_exchange.json"
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:0>10}.json"


def add_args(p):
    p.add_argument("--details", type=int, default=0, help="also fetch filer details for the first N companies (10 req/s)")
    p.add_argument("--details-all", action="store_true", help="fetch details for every company (~10k requests, ~20 min)")


def run(ing, args):
    ing.log("downloading ticker list")
    data = ing.get(TICKERS).json()
    fields, rows = data["fields"], data["data"]
    idx = {f: i for i, f in enumerate(fields)}
    orgs = []
    for i, r in enumerate(rows):
        if args.limit and i >= args.limit:
            break
        cik = str(int(r[idx["cik"]]))
        o = ing.upsert_org(r[idx["name"]].title() if r[idx["name"]].isupper() else r[idx["name"]], cik, cik=cik,
                           ticker=r[idx["ticker"]], exchange=r[idx["exchange"]] or None, country="US",
                           source_url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}")
        if o:
            orgs.append(o.id)
    ing.commit()
    ing.progress()
    n = len(orgs) if args.details_all else args.details
    if not n:
        return
    ing.log(f"fetching filer details for {n} companies")
    from app.models import Organization
    for k, oid in enumerate(orgs[:n]):
        o = ing.db.get(Organization, oid)
        r = ing.get(SUBMISSIONS.format(cik=o.cik), headers={"Host": "data.sec.gov"})
        if r.status_code != 200:
            continue
        j = r.json()
        addr = (j.get("addresses") or {}).get("business") or {}
        ing.upsert_org(o.name, o.cik, sic_code=j.get("sic") or None, industry=j.get("sicDescription") or None,
                       website=j.get("website") or None, phone=j.get("phone") or None,
                       city=(addr.get("city") or "").title() or None, state=addr.get("stateOrCountry") or None,
                       postal_code=addr.get("zipCode") or None, address=addr.get("street1") or None,
                       status="active" if j.get("filings") else None)
        if k % 200 == 0:
            ing.commit()
            ing.progress()
        time.sleep(0.11)
