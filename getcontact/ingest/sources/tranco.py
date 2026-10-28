"""Tranco research ranking of the top 1M domains (free, CC-BY). Seeds organizations by domain so the
email engine can produce addresses for any company whose domain is known.

    python -m ingest.run tranco --limit 100000
"""
import csv
import io
import os
import zipfile

URL = "https://tranco-list.eu/top-1m.csv.zip"
SKIP_TLD = (".gov", ".edu", ".mil")
SKIP = {"google.com", "facebook.com", "youtube.com", "wikipedia.org", "twitter.com", "instagram.com", "gmail.com", "yahoo.com", "hotmail.com"}


def add_args(p):
    p.add_argument("--keep", action="store_true")


def run(ing, args):
    os.makedirs("data", exist_ok=True)
    dest = os.path.join("data", "tranco.zip")
    if not os.path.exists(dest):
        ing.log("downloading tranco top-1m")
        ing.download(URL, dest)
    n = 0
    with zipfile.ZipFile(dest) as z:
        with z.open(z.namelist()[0]) as f:
            for rank, dom in csv.reader(io.TextIOWrapper(f, encoding="utf-8")):
                dom = dom.lower().strip()
                if dom in SKIP or dom.endswith(SKIP_TLD) or dom.count(".") > 2:
                    continue
                label = dom.split(".")[0]
                ing.upsert_org(label.capitalize(), dom, domain=dom, website=f"https://{dom}", source_url=f"https://tranco-list.eu/", description=f"Tranco rank {rank}")
                n += 1
                if n % 20000 == 0:
                    ing.commit()
                    ing.progress()
                if args.limit and n >= args.limit:
                    break
    ing.commit()
    if not args.keep:
        os.remove(dest)
