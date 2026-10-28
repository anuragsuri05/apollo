# getcontact

An open, self-hosted B2B contact platform modelled on Apollo.io: a people + company library, Apollo-compatible search and enrichment API, email-pattern engine, contacts, lists, sequences, CSV export, a Chrome extension, and a CLI that fills the library from every free, legitimately redistributable source we could find.

Everything is free. There are no paid tiers; the "credits" ledger exists only so the API behaves like Apollo's.

## Honest expectations

Apollo advertises ~275M contacts. That number comes from paid data partners, users' mailboxes/CRMs contributed through its data network, and years of web crawling. No set of free sources reproduces that. What the free sources do give you:

| Source | What you get | Scale (approx.) |
|---|---|---|
| SEC EDGAR tickers + filer details | US public companies, SIC, website, phone, address | ~10k companies |
| SEC Forms 3/4/5 insider data sets | Named officers & directors of US public companies | ~30–40k people / quarter |
| SEC Form D data sets | Private companies raising capital + their executives | ~15k companies, ~40k people / quarter |
| GLEIF LEI registry | Legal entities worldwide with addresses | 2.5M+ companies |
| UK Companies House bulk + officers API | All UK companies; officers via free key | ~5M companies, millions of officers |
| Wikidata | Companies with websites + CEOs/founders/chairs/boards | ~100k companies, ~50k people |
| Tranco top-1M | Domains, so the email engine can address any company | 1M domains |
| India MCA via data.gov.in | Indian registered companies (free key) | ~2M companies |
| OpenCorporates | Companies + officers (free non-commercial token) | 200M+ companies |
| Hunter.io (BYO free key) | Verified emails + the domain's email pattern | 25 domains / month |
| Apollo.io (BYO free key) | Enrich people you already hold | your credits |
| CSV import | Your own CRM / exports | unlimited |

Realistic outcome of `scripts/build_full.sh`: **~10M companies and a few million named people**, with pattern-based (not verified) emails for anyone whose company domain is known. Verified emails only come from Hunter/Apollo/your own data. The code is built to scale further on Postgres; growing past that means buying data or contributing your own.

## The flywheel (how Apollo actually got its data, rebuilt here)

Registries give you companies and officers. Apollo's *verified* emails and phones come from a different loop, and getcontact implements all of it:

| Mechanism | Apollo | getcontact |
|---|---|---|
| Contributor network: connected mailboxes/CRMs share the business contacts they see | yes, default-on | **Contribute → consent toggle** (default off), IMAP sync (Gmail app password or any host), HubSpot private-app token, MBOX/EML/CSV upload (Google Takeout, Apple Mail, Thunderbird, Google Contacts, Outlook, LinkedIn connections, CRM exports) |
| Signature parsing: title + phone from the sender's sign-off | yes | `app/contrib.py` extracts title and phone from the last lines of each message |
| Bounce feedback: delivery failures retire addresses | yes | sending mailbox marked `is_sender` is scanned; DSNs flip the email to `invalid`, stop the sequence, raise a `bounce` signal |
| Reply feedback: replies verify addresses and stop sequences | yes | reply from an enrolled contact → `verified`, enrollment `replied`, contact stage `replied` |
| Job-change signals from auto-replies ("no longer with…") | yes | `job_change` signal, email invalidated, the successor named in the auto-reply is captured as a new contact |
| Open tracking | yes | 1×1 pixel at `/api/v1/t/{token}/{step}.gif`, counted once per step |
| Public web crawl of company sites | yes | `ingest.run webcrawl`: robots-aware team/about/contact page crawler → people + titles, published emails (verified), phones, LinkedIn |
| Bulk SMTP verification | yes | `ingest.run verify_emails` with per-domain throttling and catch-all detection |
| Pattern inference across a domain | yes | learned from every verified email, applied to everyone else at that company |
| Opt-out | yes | public `/api/v1/optout` page + `List-Unsubscribe` header on every send; suppressed addresses are never revealed, exported or emailed |

What this does **not** do: harvest LinkedIn, buy data, or share anything without the user ticking the consent box. The size of the verified library is a function of how many mailboxes your users connect, exactly as it is for Apollo. The worker (`python -m app.worker`) syncs every connected account every `MAIL_SYNC_MINUTES`.

Smoke-test the loop end to end with synthetic fixtures:

```bash
uvicorn app.main:app --port 8000 &
python scripts/test_flywheel.py http://localhost:8000 tests/fixtures
```

## Quick start (SQLite, no Docker)

```bash
cd getcontact
pip install -r requirements.txt
cp .env.example .env            # edit USER_AGENT (SEC requires a contact email in it)
scripts/bootstrap.sh            # ~10 min seed, no keys needed
uvicorn app.main:app --reload   # http://localhost:8000  (OpenAPI at /docs)
```

Sign up in the browser; your master API key is shown once under **API**.

## Production (Postgres)

```bash
docker compose up -d db
export DATABASE_URL=postgresql+psycopg://getcontact:getcontact@localhost:5432/getcontact
scripts/build_full.sh           # hours; run connectors in parallel shells if you like
docker compose up -d api worker
```

## Ingestion CLI

```bash
python -m ingest.run list
python -m ingest.run sec_edgar --details-all
python -m ingest.run sec_insiders --quarters 8
python -m ingest.run sec_formd --quarters 8
python -m ingest.run wikidata [--country IN]
python -m ingest.run gleif --country IN --status ACTIVE
python -m ingest.run companies_house --active-only            # bulk file
COMPANIES_HOUSE_API_KEY=… python -m ingest.run companies_house --skip-bulk --officers 5000
python -m ingest.run tranco --limit 300000
DATA_GOV_IN_API_KEY=… python -m ingest.run data_gov_in --resource <resource-id>
OPENCORPORATES_TOKEN=… python -m ingest.run opencorporates --query "" --jurisdiction in
HUNTER_API_KEY=… python -m ingest.run hunter --from-db 25
APOLLO_API_KEY=… python -m ingest.run apollo --limit 100 --seniority c_suite,vp
python -m ingest.run csv --file leads.csv --source-name my_crm
python -m ingest.run webcrawl --from-db 500                  # company team pages → people, emails, phones
python -m ingest.run guess_emails --seniority c_suite,vp,director
python -m ingest.run verify_emails --limit 2000 --workers 6   # SMTP-verify guesses
python -m ingest.run mx_check
```

Connectors are idempotent and dedupe across sources by domain, LEI and CIK; people dedupe by (name, company). Every record keeps `source` and `source_url` for provenance.

## API (Apollo-compatible)

Header: `x-api-key: gc_…`. Base: `/api/v1`.

| Endpoint | Credits | Notes |
|---|---|---|
| `POST /mixed_people/api_search` | 0 | same filter names as Apollo (`person_titles[]`, `person_seniorities[]`, `person_locations[]`, `q_organization_domains_list[]`, `organization_num_employees_ranges[]`, …); 100/page, 500 pages; returns `has_email`, never the email |
| `POST /people/match` | 1 (+8 phone) | by `id`, `linkedin_url`, `email`, or `first_name`+`last_name`+`domain`/`organization_name`; unknown people get a pattern-based email with `match_confidence: low` |
| `POST /people/bulk_match` | per match | `{"details":[…≤10]}` |
| `POST /mixed_companies/search` | 0 | |
| `POST /organizations/enrich?domain=` | 0 | returns email pattern + MX status |
| `GET/POST /contacts`, `/lists`, `/lists/{id}/items`, `/sequences`, `/sequences/{id}/steps|enroll|run` | 0 | workspace |
| `GET /people/export.csv?…&reveal=true` | 1/row | export a search |
| `GET /usage_stats/api_usage_stats` | 0 | master key |
| `GET /stats` | 0 | library size, by source/country |
| `POST /contribute/consent`, `GET /contribute/stats`, `POST /contribute/upload` (multipart mbox/eml/csv, `watch=true` for a sending mailbox) | 0 | contributor network |
| `GET/POST/DELETE /mail_accounts`, `POST /mail_accounts/{id}/sync` | 0 | IMAP / HubSpot connections |
| `GET /signals?kind=` | 0 | bounce, reply, job_change, auto_reply, open, new_contact |
| `POST /optout` (public), `GET /optout` page | 0 | suppression |

Rate limits are per team with `x-rate-limit-*` headers and 429 + `retry-after`, like Apollo.

## Email engine

Search is free and never shows emails. On reveal, the engine returns the stored email if one exists, otherwise renders the company's learned pattern (`{first}.{last}`, `{f}{last}`, …) and checks MX. Statuses: `verified` (from Hunter/Apollo/CSV or an SMTP probe), `mx_valid` (learned pattern + MX present), `guessed` (default pattern), `invalid`. Set `SMTP_VERIFY=1` to probe mailboxes on reveal (slow; many hosts block it).

## Chrome extension

`chrome://extensions` → Developer mode → Load unpacked → `extension/`. Enter the server URL and an API key. On a LinkedIn profile or any company site it pre-fills name/title/company from the visible page, finds the email in your library, and saves to Contacts. It only reads the page you have open; it does not crawl.

## Layout

```
app/          FastAPI: models, auth, credits, email_engine, search, contrib (contributor parsing),
              mail_sync (IMAP/HubSpot/MBOX + bounce/reply/job-change detection), routers/, static UI, worker
ingest/       base.py (upserts, dedup, HTTP), run.py (CLI), sources/<connector>.py (incl. webcrawl, verify_emails)
extension/    Manifest V3 popup
scripts/      bootstrap.sh (10 min seed), build_full.sh (everything), test_flywheel.py (end-to-end smoke test)
tests/        synthetic .example fixtures for the smoke test
```

## Compliance notes

Names and roles of company officers are public-record data published by regulators for exactly this purpose. Email addresses generated by the pattern engine are inferences; mark outreach accordingly and honour opt-outs. If you sell into the EU/UK, document a legitimate-interest assessment, add a privacy notice to first contact, and purge on request. Do not point the CSV importer at scraped LinkedIn exports; LinkedIn enforces its terms against that, and the Proxycurl shutdown in 2025 shows how that ends.
