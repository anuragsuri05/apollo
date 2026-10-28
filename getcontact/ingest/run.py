"""getcontact ingestion CLI.

    python -m ingest.run <source> [options]
    python -m ingest.run list

Every connector is idempotent: re-running updates rows in place.
"""
import argparse
import importlib
import sys
import traceback

from .base import Ingestor

SOURCES = {
    "sec_edgar":       "SEC EDGAR company tickers + filer details (US public companies, ~10k)",
    "sec_insiders":    "SEC Forms 3/4/5 insider datasets → officers & directors of US public companies",
    "sec_formd":       "SEC Form D datasets → executives/directors of private companies raising capital",
    "gleif":           "GLEIF LEI registry → 2.5M+ legal entities worldwide (filter by country)",
    "companies_house": "UK Companies House bulk file (5M companies) + officers via free API key",
    "wikidata":        "Wikidata companies with websites + their CEOs/founders/chairs/board members",
    "tranco":          "Tranco top-1M domains → seed organizations by domain",
    "data_gov_in":     "India MCA company master data via data.gov.in (free API key)",
    "opencorporates":  "OpenCorporates companies + officers (free non-commercial token)",
    "hunter":          "Hunter.io domain search (BYO free key) → verified emails + domain pattern",
    "apollo":          "Apollo.io people/match (BYO free key) → enrich people already in the DB",
    "csv":             "Generic CSV import (people and/or companies)",
    "webcrawl":        "Company websites → team pages (people + titles), published emails, phones, LinkedIn",
    "guess_emails":    "Offline: generate pattern-based emails for people whose company has a domain",
    "verify_emails":   "Offline: SMTP-verify guessed emails in bulk (verified / invalid)",
    "mx_check":        "Offline: validate MX records for organization domains",
}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m ingest.run", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="source", required=True)
    sub.add_parser("list", help="list connectors")
    mods = {}
    for name in SOURCES:
        mod = importlib.import_module(f"ingest.sources.{name}")
        mods[name] = mod
        p = sub.add_parser(name, help=SOURCES[name])
        p.add_argument("--limit", type=int, default=0, help="max rows (0 = all)")
        mod.add_args(p)
    args = ap.parse_args(argv)
    if args.source == "list":
        for k, v in SOURCES.items():
            print(f"{k:16} {v}")
        return 0
    ing = Ingestor(args.source, args)
    try:
        mods[args.source].run(ing, args)
        ing.commit()
        ing.finish()
        return 0
    except KeyboardInterrupt:
        ing.commit()
        ing.finish("interrupted")
        return 130
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        ing.commit()
        ing.finish(repr(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
