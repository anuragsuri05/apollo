#!/usr/bin/env bash
# Quick seed (~10 minutes, no API keys): a few hundred thousand companies and tens of thousands of named executives.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
python3 -m ingest.run sec_edgar --details 500
python3 -m ingest.run sec_insiders --quarters 2
python3 -m ingest.run sec_formd --quarters 2
python3 -m ingest.run wikidata --limit 20000
python3 -m ingest.run gleif --country IN --limit 5000
python3 -m ingest.run tranco --limit 50000
python3 -m ingest.run guess_emails --seniority c_suite,vp,director,founder,owner
echo "Done. Start the app:  uvicorn app.main:app --reload   →  http://localhost:8000"
