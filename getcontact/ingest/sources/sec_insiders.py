"""SEC Forms 3/4/5 insider-transactions data sets → named officers and directors of US public companies.

https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets  (quarterly zips, free)
"""
import csv
import io
import os
import tempfile
import zipfile
from datetime import date

from app.util import sec_name_to_first_last

# SEC moves data sets between folders as they age; try each prefix in order.
SEC_FOLDERS = ("datastandardsinnovation", "structureddata", "dera")
URL = "https://www.sec.gov/files/{folder}/data/insider-transactions-data-sets/{q}_form345.zip"


def sec_download(ing, dest, url_tpl, q):
    """Download the first prefix variant that exists; raise if none does."""
    last = None
    for folder in SEC_FOLDERS:
        url = url_tpl.format(folder=folder, q=q)
        try:
            return ing.download(url, dest)
        except Exception as e:  # noqa: BLE001
            last = e
            if os.path.exists(dest):
                os.remove(dest)
            if "404" not in str(e):
                raise
    raise last


def latest_quarters(n):
    d = date.today()
    q = (d.month - 1) // 3  # 0-based current quarter
    out = []
    y = d.year
    q -= 1  # last complete quarter
    if q < 0:
        q, y = 3, y - 1
    for _ in range(n):
        out.append(f"{y}q{q + 1}")
        q -= 1
        if q < 0:
            q, y = 3, y - 1
    return out


def add_args(p):
    p.add_argument("--quarter", action="append", help="e.g. 2026q2 (repeatable). Default: last complete quarter")
    p.add_argument("--quarters", type=int, default=1, help="how many recent quarters when --quarter not given")
    p.add_argument("--keep", action="store_true", help="keep downloaded zips in ./data")


def _read_tsv(z, name):
    # the TextIOWrapper keeps the zip member open for as long as the reader is iterated
    return csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8", errors="replace"), delimiter="\t")


def run(ing, args):
    # SEC publishes each quarter's data set weeks after quarter end, so when quarters are auto-picked we
    # try a few extra candidates and stop once the requested number have actually been found.
    wanted = len(args.quarter) if args.quarter else args.quarters
    quarters = args.quarter or latest_quarters(args.quarters + 3)
    os.makedirs("data", exist_ok=True)
    total = found = 0
    for q in quarters:
        if found >= wanted:
            break
        dest = os.path.join("data", f"{q}_form345.zip")
        if not os.path.exists(dest):
            ing.log(f"downloading {q} insider data set")
            try:
                sec_download(ing, dest, URL, q)
            except Exception as e:  # noqa: BLE001
                ing.log(f"skip {q}: {str(e).splitlines()[0]}")
                continue
        found += 1
        with zipfile.ZipFile(dest) as z:
            names = {n.upper(): n for n in z.namelist()}
            issuers = {}
            for r in _read_tsv(z, names["SUBMISSION.TSV"]):
                issuers[r["ACCESSION_NUMBER"]] = (r.get("ISSUERCIK"), r.get("ISSUERNAME"), r.get("ISSUERTRADINGSYMBOL"))
            ing.log(f"{q}: {len(issuers)} filings")
            seen = set()
            for r in _read_tsv(z, names["REPORTINGOWNER.TSV"]):
                if args.limit and total >= args.limit:
                    break
                cik, iname, sym = issuers.get(r["ACCESSION_NUMBER"], (None, None, None))
                if not cik or not iname:
                    continue
                key = (r.get("RPTOWNERCIK"), cik)
                if key in seen:
                    continue
                seen.add(key)
                org = ing.upsert_org(iname.title() if iname.isupper() else iname, str(int(cik)), source="sec_edgar", cik=str(int(cik)),
                                     ticker=sym or None, country="US")
                rel = (r.get("RPTOWNER_RELATIONSHIP") or "").strip()
                title = (r.get("RPTOWNER_TITLE") or "").strip()
                if not title:
                    if "Director" in rel:
                        title = "Director"
                    elif "Officer" in rel:
                        title = "Officer"
                    else:
                        continue  # 10% owners without a title are usually funds
                first, last, full = sec_name_to_first_last(r.get("RPTOWNERNAME") or "")
                if not full:
                    continue
                ing.upsert_person(full, f"{r.get('RPTOWNERCIK')}:{int(cik)}", org, first_name=first, last_name=last, title=title,
                                  city=(r.get("RPTOWNER_CITY") or "").title() or None, state=r.get("RPTOWNER_STATE") or None, country="US",
                                  source_url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={r.get('RPTOWNERCIK')}")
                total += 1
                if total % 5000 == 0:
                    ing.commit()
                    ing.progress()
        ing.commit()
        if not args.keep:
            os.remove(dest)
