#!/usr/bin/env bash
# Full build of every free source. Expect many hours and ~10 GB on Postgres. Run pieces in parallel on separate shells if you like.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m ingest.run sec_edgar --details-all
python3 -m ingest.run sec_insiders --quarters 20          # 5 years of officers/directors
python3 -m ingest.run sec_formd --quarters 20             # 5 years of private-company execs
python3 -m ingest.run wikidata                             # all companies with websites
python3 -m ingest.run companies_house --active-only        # ~5M UK companies
for c in US IN GB DE FR CA AU SG AE NL CH JP; do python3 -m ingest.run gleif --country $c; done
python3 -m ingest.run tranco                               # 1M domains
# optional, need free keys in .env:
# python3 -m ingest.run companies_house --skip-bulk --officers 100000
# python3 -m ingest.run data_gov_in --resource <id>
# python3 -m ingest.run opencorporates --query "" --jurisdiction in
# python3 -m ingest.run hunter --from-db 25
python3 -m ingest.run mx_check
python3 -m ingest.run guess_emails
