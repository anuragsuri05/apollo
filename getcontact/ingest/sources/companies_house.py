"""UK Companies House.

Bulk basic company data (free, ~450MB zip, ~5M rows):
    python -m ingest.run companies_house --limit 200000
Officers via the free REST API (register at developer.company-information.service.gov.uk, 600 req / 5 min):
    COMPANIES_HOUSE_API_KEY=... python -m ingest.run companies_house --officers 500 --skip-bulk
"""
import csv
import io
import os
import time
import zipfile
from datetime import date

from app.config import COMPANIES_HOUSE_API_KEY
from app.models import Organization

BULK = "https://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile-{d}.zip"
OFFICERS = "https://api.company-information.service.gov.uk/company/{num}/officers"


def add_args(p):
    p.add_argument("--skip-bulk", action="store_true")
    p.add_argument("--officers", type=int, default=0, help="fetch officers for N active UK companies lacking people")
    p.add_argument("--active-only", action="store_true")
    p.add_argument("--keep", action="store_true")


def run(ing, args):
    if not args.skip_bulk:
        os.makedirs("data", exist_ok=True)
        d = date.today().replace(day=1).isoformat()
        dest = os.path.join("data", f"ch-{d}.zip")
        if not os.path.exists(dest):
            ing.log("downloading Companies House bulk file (~450MB)")
            ing.download(BULK.format(d=d), dest)
        n = 0
        with zipfile.ZipFile(dest) as z:
            name = z.namelist()[0]
            with z.open(name) as f:
                rd = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"))
                for r in rd:
                    r = {k.strip(): v for k, v in r.items()}
                    status = (r.get("CompanyStatus") or "").lower()
                    if args.active_only and "active" not in status:
                        continue
                    sic = (r.get("SICCode.SicText_1") or "").strip()
                    code, _, desc = sic.partition(" - ")
                    inc = r.get("IncorporationDate") or ""
                    ing.upsert_org(r["CompanyName"].title(), r["CompanyNumber"], company_number=r["CompanyNumber"], country="GB",
                                   city=(r.get("RegAddress.PostTown") or "").title() or None, state=r.get("RegAddress.County") or None,
                                   postal_code=r.get("RegAddress.PostCode") or None, address=r.get("RegAddress.AddressLine1") or None,
                                   sic_code=code if code.isdigit() else None, industry=desc or None, status=status or None,
                                   founded_year=int(inc[-4:]) if inc[-4:].isdigit() else None,
                                   source_url=f"https://find-and-update.company-information.service.gov.uk/company/{r['CompanyNumber']}")
                    n += 1
                    if n % 20000 == 0:
                        ing.commit()
                        ing.progress()
                    if args.limit and n >= args.limit:
                        break
        ing.commit()
        if not args.keep:
            os.remove(dest)
    if args.officers:
        if not COMPANIES_HOUSE_API_KEY:
            ing.log("COMPANIES_HOUSE_API_KEY not set — skipping officers")
            return
        from sqlalchemy import exists
        from app.models import Person
        q = ing.db.query(Organization).filter(Organization.source == "companies_house", Organization.status.like("active%")).filter(
            ~exists().where(Person.organization_id == Organization.id)).limit(args.officers)
        for i, o in enumerate(q.all()):
            r = ing.get(OFFICERS.format(num=o.company_number), auth=(COMPANIES_HOUSE_API_KEY, ""), params={"items_per_page": 50})
            if r.status_code != 200:
                continue
            for it in r.json().get("items", []):
                if it.get("resigned_on"):
                    continue
                nm = it.get("name") or ""
                if "," in nm:  # "SURNAME, Forename"
                    last, first = [x.strip().title() for x in nm.split(",", 1)]
                    first = first.split()[0] if first else ""
                    full = f"{first} {last}".strip()
                else:
                    full, first, last = nm.title(), None, None
                role = (it.get("officer_role") or "").replace("-", " ").title()
                if it.get("occupation") and it["occupation"].lower() not in ("none", "director", "n/a"):
                    role = f"{it['occupation'].title()} ({role})"
                addr = it.get("address") or {}
                ing.upsert_person(full, f"{o.company_number}:{(it.get('links') or {}).get('officer', {}).get('appointments', nm)}", o,
                                  first_name=first, last_name=last, title=role, city=(addr.get("locality") or "").title() or None,
                                  country=(it.get("country_of_residence") or "")[:2].upper() or "GB",
                                  source_url=f"https://find-and-update.company-information.service.gov.uk/company/{o.company_number}/officers")
            if i % 50 == 0:
                ing.commit()
                ing.progress()
            time.sleep(0.5)
