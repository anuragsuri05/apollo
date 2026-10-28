"""GLEIF Legal Entity Identifier registry (2.5M+ entities worldwide). Free JSON API, no key, ~60 req/min.

    python -m ingest.run gleif --country IN --limit 20000
    python -m ingest.run gleif --country US --status ACTIVE
"""
import time

API = "https://api.gleif.org/api/v1/lei-records"


def add_args(p):
    p.add_argument("--country", action="append", help="ISO-2 country filter (repeatable)")
    p.add_argument("--status", default="ACTIVE", help="ACTIVE | INACTIVE | '' for all")
    p.add_argument("--page-size", type=int, default=200)
    p.add_argument("--start-page", type=int, default=1)


def run(ing, args):
    countries = args.country or [None]
    total = 0
    for c in countries:
        page = args.start_page
        while True:
            params = {"page[size]": args.page_size, "page[number]": page}
            if c:
                params["filter[entity.legalAddress.country]"] = c
            if args.status:
                params["filter[entity.status]"] = args.status
            r = ing.get(API, params=params, headers={"Accept": "application/vnd.api+json"})
            if r.status_code != 200:
                ing.log(f"HTTP {r.status_code}: {r.text[:200]}")
                break
            j = r.json()
            data = j.get("data") or []
            if not data:
                break
            for rec in data:
                a = rec["attributes"]
                ent = a["entity"]
                addr = ent.get("legalAddress") or {}
                name = (ent.get("legalName") or {}).get("name")
                ing.upsert_org(name, a["lei"], lei=a["lei"], country=addr.get("country"), city=(addr.get("city") or "").title() or None,
                               state=addr.get("region") or None, postal_code=addr.get("postalCode") or None,
                               address=", ".join(addr.get("addressLines") or []) or None, status=(ent.get("status") or "").lower() or None,
                               source_url=f"https://search.gleif.org/#/record/{a['lei']}")
                total += 1
                if args.limit and total >= args.limit:
                    ing.commit()
                    return
            ing.commit()
            if page % 10 == 0:
                ing.progress()
            last = (j.get("meta") or {}).get("pagination", {}).get("lastPage")
            if last and page >= last:
                break
            page += 1
            time.sleep(1.0)
