"""SEC Form D data sets → private companies raising capital + their executive officers / directors / promoters.

https://www.sec.gov/data-research/sec-markets-data/form-d-data-sets  (quarterly zips, free)
"""
import csv
import io
import os
import zipfile

from .sec_insiders import latest_quarters, sec_download

URL = "https://www.sec.gov/files/{folder}/data/form-d-data-sets/{q}_d.zip"
INDUSTRY = {}  # filled from OFFERING.tsv


def add_args(p):
    p.add_argument("--quarter", action="append", help="e.g. 2026q2 (repeatable)")
    p.add_argument("--quarters", type=int, default=1)
    p.add_argument("--keep", action="store_true")


def _tsv(z, name):
    return csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8", errors="replace"), delimiter="\t")


def run(ing, args):
    wanted = len(args.quarter) if args.quarter else args.quarters
    quarters = args.quarter or latest_quarters(args.quarters + 3)
    os.makedirs("data", exist_ok=True)
    total = found = 0
    for q in quarters:
        if found >= wanted:
            break
        dest = os.path.join("data", f"{q}_d.zip")
        if not os.path.exists(dest):
            ing.log(f"downloading Form D {q}")
            try:
                sec_download(ing, dest, URL, q)
            except Exception as e:  # noqa: BLE001
                ing.log(f"skip {q}: {str(e).splitlines()[0]}")
                continue
        found += 1
        with zipfile.ZipFile(dest) as z:
            names = {os.path.basename(n).upper(): n for n in z.namelist()}
            offering = {}
            if "OFFERING.TSV" in names:
                for r in _tsv(z, names["OFFERING.TSV"]):
                    offering[r["ACCESSIONNUMBER"]] = (r.get("INDUSTRYGROUPTYPE"), r.get("REVENUERANGE"))
            orgs = {}
            for r in _tsv(z, names["ISSUERS.TSV"]):
                if (r.get("IS_PRIMARYISSUER_FLAG") or "YES").upper() != "YES":
                    continue  # primary issuer only
                acc = r["ACCESSIONNUMBER"]
                cik = r.get("CIK")
                name = r.get("ENTITYNAME") or ""
                if not cik or not name:
                    continue
                ind, rev = offering.get(acc, (None, None))
                st = r.get("STATEORCOUNTRY") or None
                country = "US" if st and len(st) == 2 and st.isalpha() and st not in ("X1",) else None
                o = ing.upsert_org(name.title() if name.isupper() else name, str(int(cik)), source="sec_edgar", cik=str(int(cik)),
                                   industry=ind or None, city=(r.get("CITY") or "").title() or None, state=st, country=country,
                                   postal_code=r.get("ZIPCODE") or None, address=r.get("STREET1") or None, phone=r.get("ISSUERPHONENUMBER") or None,
                                   founded_year=int(r["YEAROFINC_VALUE_ENTERED"]) if (r.get("YEAROFINC_VALUE_ENTERED") or "").isdigit() else None,
                                   source_url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}")
                if o:
                    orgs[acc] = o
            ing.commit()
            ing.log(f"{q}: {len(orgs)} issuers")
            for r in _tsv(z, names["RELATEDPERSONS.TSV"]):
                if args.limit and total >= args.limit:
                    break
                o = orgs.get(r["ACCESSIONNUMBER"])
                if not o:
                    continue
                first, last = (r.get("FIRSTNAME") or "").strip().title(), (r.get("LASTNAME") or "").strip().title()
                if not (first and last):
                    continue
                roles = [r.get(k) for k in ("RELATIONSHIP_1", "RELATIONSHIP_2", "RELATIONSHIP_3") if r.get(k)]
                clar = (r.get("RELATIONSHIPCLARIFICATION") or "").strip()
                title = clar if 2 < len(clar) < 120 else ", ".join(roles) or "Executive Officer"
                ing.upsert_person(f"{first} {last}", f"{o.cik}:{first.lower()}.{last.lower()}", o, first_name=first, last_name=last, title=title,
                                  city=(r.get("CITY") or "").title() or None, state=r.get("STATEORCOUNTRY") or None, country=o.country,
                                  source_url=o.source_url)
                total += 1
                if total % 5000 == 0:
                    ing.commit()
                    ing.progress()
        ing.commit()
        if not args.keep:
            os.remove(dest)
