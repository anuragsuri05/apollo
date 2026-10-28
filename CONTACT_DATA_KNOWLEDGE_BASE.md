# Contact Data Providers Knowledge Base
## Apollo.io end-to-end + every major people-contact data vendor

**Compiled:** 2026-10-16 · **Status:** reference doc for Claude + Laksh
**Verification key:** ✅ = read from vendor's own page/docs · ⚠️ = third-party blogs only (figures conflict; re-check before budgeting)

---

## 0. TL;DR decision table

| Need | Pick | Why |
|---|---|---|
| Cheapest all-in-one (DB + sequences + dialer) | **Apollo.io** | ~$49–119/seat/mo, 275M contacts, built-in outreach |
| Best US email accuracy at scale, enterprise | **ZoomInfo** | Largest single-source; quote-only, ~$15k+/yr |
| Best EU/UK mobile numbers + GDPR posture | **Cognism** | Phone-verified "Diamond" mobiles; quote-only |
| Individual rep, pay-as-you-go reveals | **Lusha** or **Kaspr** | Credit-based, Chrome extension, free tiers |
| Cheapest bulk email lookups | **RocketReach** (Essentials) or **Hunter** | $19–49/mo entry, email-first |
| Developer API, person enrichment at volume | **People Data Labs** | $98/mo for 350 records; Enterprise data licensing |
| Max accuracy via multi-vendor "waterfall" | **Clay** | Orchestrates 150+ providers; pay per step that returns data |
| India-specific mobiles / DPDP compliance | **Zintlr / EasyLeadz / Pintel.ai** | MCA-sourced Indian decision-maker data |
| Email finding + verification only | **Hunter.io**, **Snov.io**, **Findymail**, **Prospeo** | 0.5–1 credit per op |

**Rule of thumb for outbound:** search/list-build in Apollo (0 credits) → enrich emails in Apollo (1 credit) → verify with a dedicated verifier (ZeroBounce/NeverBounce/Hunter 0.5 credit) → waterfall phone numbers via Clay/Cognism only for high-value accounts (8+ credits each in Apollo).

---

## 1. Apollo.io — complete profile

### 1.1 What it is
Apollo.io is a B2B sales-intelligence + engagement platform: a contact/company database, a Chrome extension for LinkedIn/Gmail, email sequencing, a dialer, CRM sync, intent data, and a REST API. Think "ZoomInfo + Outreach in one, at SMB prices."

### 1.2 Database (⚠️ third-party, consistent across reviews)
- **~275M contacts, ~73M companies** (older reviews cite 210M/30M; Apollo's own marketing has cited 240M+ → number grows over time).
- **Sources:** public web, user-contributed data (Apollo's "data network" from users' mailboxes/CRMs), third-party partners. Refresh claim: 270M+ records processed monthly.
- **Accuracy:** Apollo claims 97% email accuracy. Independent audits: ~91% email, ~65% phone on a 50k sample; G2 data-accuracy score 8.3/10. Applying the "Verified Email" filter shrinks the DB from 275M → ~96M. Cold-outbound bounce reports of 30–35% appear in competitor blogs (treat with caution). **US/mid-market strongest; APAC, LATAM, enterprise weakest.**

### 1.3 Plans and pricing (✅ structure from apollo.io/pricing; ⚠️ dollar figures from Oct-2026 third-party snapshots)
| Plan | Annual $/seat/mo | Monthly $/seat/mo | Key inclusions |
|---|---|---|---|
| Free | $0 | $0 | Gmail-only sending, 2 active sequences, limited CRM, up to ~10k record select |
| Basic | ~$49 | ~$65 | Unlimited sequences, Salesforce/HubSpot sync, Microsoft 365 sending, core integrations |
| Professional | ~$79 | ~$99 | Higher credits, AI features, call recording, US dialer, advanced CRM integrations |
| Organization / Custom | ~$119 (annual only, 3-seat min) | n/a | International dialer, custom reports, SSO, advanced security, dedicated support, **API access listed here** |

Facts from Apollo's pricing page (✅): all seats share one plan level; credits are pooled at team level, granted at cycle start, **do not roll over**; admins can set per-user caps; add-on credits can be bought mid-cycle and auto-renew; annual = 12-month commitment, monthly cancel-anytime at higher rate.

### 1.4 Credits (✅ from docs.apollo.io + knowledge.apollo.io; allowances ⚠️)
- **Email reveal:** 1 credit (only verified, net-new emails are charged; bounced sent emails refundable within 30 days).
- **Mobile phone reveal:** +8 credits (charged once per contact even if multiple numbers returned; **no refunds on mobiles**).
- **Demographic-only enrichment:** 1 credit. **No match / no new data:** 0 credits.
- **Organization search API:** 1 credit per page (100 results). **People search API:** 0 credits.
- **Overage:** ~$0.20/credit, 250-credit minimum (⚠️).
- **Allowances (⚠️ conflicting):** Free ≈ 100–1,200 email credits/mo depending on corporate vs Gmail domain + 5 mobile + 10 export credits/mo; Basic ≈ 2,500/mo (30k/yr); Pro ≈ 4,000/mo (48k/yr); Org ≈ 6,000/mo (72k/yr). Check Settings → Billing → Credit usage in-app.
- Other credit categories: enrichment, job-change alerts, AI research, email infrastructure, waterfall enrichment.

### 1.5 Core features
- **Search / filters:** title, seniority, location, keywords, email status, industry, NAICS/SIC, headcount, revenue, technographics, funding, job postings, headcount growth, lookalikes (same filters as the API below).
- **Chrome extension:** works on LinkedIn, Sales Navigator, Gmail, company sites; reveals email/phone, adds to lists/sequences/CRM. Billed against credits (1 email / 8 phone).
- **Sequences:** multi-step email + call + LinkedIn tasks; A/B testing; Free = 2 active sequences, Gmail only.
- **Dialer:** US dialer on Professional; international on Organization; call recording on Pro+.
- **CRM:** Salesforce, HubSpot (paid), Pipedrive, Zoho, etc.; bi-directional sync, enrichment of CRM records.
- **Intent data:** Bombora-sourced topics on Pro+; website-visitor ID.
- **AI:** AI email writing, AI research agents, lead scoring (Pro+).
- **Deals, tasks, conversations (call intelligence), analytics.**

### 1.6 API (✅ verified from docs.apollo.io)
- **Base URL:** `https://api.apollo.io/api/v1/`
- **Auth:** header `x-api-key: <key>` (or OAuth bearer with per-endpoint scopes). Create keys in Settings → Integrations → API. **Master API key** toggle grants all endpoints; regular keys get a subset (search/enrich/contacts/accounts). Master-only: users, deals, sequences, tasks, calls, email accounts, stages, labels, custom fields, usage stats. Scoped key on a master-only endpoint → HTTP 403.
- **Plan gating:** docs say "depends on your plan"; pricing page lists API under Custom/Org tier; third parties report Basic+ gets search/enrich. Free accounts must be registered with a work email to use search.

**Key endpoints**
| Purpose | Method + path | Credits | Notes |
|---|---|---|---|
| People search | `POST /mixed_people/api_search` | 0 | 100/page, max 500 pages (50k display cap). Returns `has_email`/`has_direct_phone` flags, **no emails/phones**. Use `api_search`, not legacy `/mixed_people/search` (403 on lower plans). |
| People enrichment | `POST /people/match` | 1–9 | Params: first_name, last_name, name, email, hashed_email (MD5/SHA-256), organization_name, domain, id, linkedin_url; `reveal_personal_emails`, `reveal_phone_number` (needs `webhook_url`), `run_waterfall_email/phone`, `poll_only`. Returns `match_confidence` high/medium/low/none. |
| Bulk people enrichment | `POST /people/bulk_match` | 1–9 each | ≤10 people per call in `details[]`; per-minute limit is 50% of single-enrich. |
| Organization search | `POST /mixed_companies/search` | 1 per page | Same filter families; funding, job postings, keywords (≤150), lookalikes (≤5 seeds). |
| Organization enrichment | `POST /organizations/enrich` | 1 | by domain |
| Contacts / Accounts CRUD | `/contacts`, `/accounts` | 0 | your saved records; general limits apply |
| Sequences | `/emailer_campaigns/...` | 0 | master key; add contacts, view stats |
| Usage & limits | `GET /usage_stats/api_usage_stats` | 0 | master key; **source of truth for your limits** |
| Poll webhook result | `/.../poll_webhook_result?request_id=` | 0 | request_id is a signed 64-bit int (can be negative) |

**People search filter params (api_search):** `person_titles[]`, `person_not_titles[]`, `person_not_past_titles[]`, `include_similar_titles`, `person_seniorities[]` (owner, founder, c_suite, partner, vp, head, director, manager, senior, entry, intern), `person_locations[]`, `person_not_locations[]`, `q_keywords`, `q_person_name`, `contact_email_status[]` (verified, unverified, likely to engage, unavailable), `organization_ids[]`, `q_organization_domains_list[]` (≤1000), `organization_locations[]`, `organization_industries[]`, `organization_industry_tag_ids[]`, `organization_naics_codes[]`, `organization_sic_codes[]`, `organization_num_employees_ranges[]` ("min,max"), `revenue_range[min|max]`, `currently_using_(all|any|not_any)_of_technology_uids[]`, `q_organization_job_titles[]`, `organization_num_jobs_range`, `organization_job_posted_at_range`, `organization_headcount_growth_past_n_months` (6/12/24) + `_range`, `lookalike_organization_ids[]`, `page`, `per_page`. Titles+not_titles combined must be <100 unique (else 422).

**Phone reveal flow:** call match with `reveal_phone_number=true&webhook_url=https://…` → sync response (no phone) → phone payload POSTed to webhook minutes later (may retry → make idempotent). Or `poll_only=true` (no webhook_url, else 400 `WEBHOOK_URL_WITH_POLL_ONLY`) and poll with `request_id`. Personal emails never revealed for GDPR-region people.

**Rate limits (✅)** — per **team** (all keys/users share), each endpoint has its own counters, fixed windows start at first request, all three windows apply at once. Exceed → 429 with `retry-after` header; `x-rate-limit-*`, `x-*-usage`, `x-*-requests-left` headers on every response.
| Window | Free | Basic | Pro | Org |
|---|---|---|---|---|
| General /min /hr /day | 50/200/600 | 200/400/2,000 | 200/400/2,000 | 200/600/6,000 |
| Search /min /hr /day | 50/200/600 | 200/6,000/50,000 | same | same |
| Enrich /min /hr /day | 50(20 bulk)/200(100)/600 | 1,000/∞/∞ | same | same |
Low-limit endpoints: analytics report 5/hr; export conversations (Free) 1/min, 20/hr.

**Minimal example**
```bash
# search (0 credits)
curl -X POST "https://api.apollo.io/api/v1/mixed_people/api_search?person_titles[]=CTO&person_locations[]=India&organization_num_employees_ranges[]=51,200&page=1&per_page=100" \
  -H "x-api-key: $APOLLO_KEY" -H "Content-Type: application/json"
# enrich one (1 credit for email)
curl -X POST "https://api.apollo.io/api/v1/people/match?first_name=Jane&last_name=Doe&domain=example.com" \
  -H "x-api-key: $APOLLO_KEY"
```

### 1.7 Strengths / weaknesses
+ Best price-to-feature ratio; search is free; huge DB; outreach built in; transparent self-serve.
− Phone accuracy mediocre; non-US coverage thin; credits don't roll over; mobiles non-refundable; API gated by plan and master-key rules; 50k display cap per search; verify emails before sending.

---

## 2. Competitor profiles (people-contact data)

### 2.1 ZoomInfo (✅ plan structure; ⚠️ prices)
- Largest single-source B2B DB; contact + company + technographic + intent (Streaming Intent add-on) + website-visitor + org charts; ReachOut Chrome extension; Copilot AI.
- **Plans:** Sales → Professional / Copilot Advanced / Copilot Enterprise (free trials); Marketing → Demand (75k credits, 25 intent topics) / ABM Lite (100 topics) / ABM Enterprise (150k credits); Talent.
- **Pricing:** quote-only, annual contracts; typical $15k–$33k+/yr (Vendr median ~$33.5k). Free "Lite" ~10 credits/mo (⚠️).
- **Credits:** 1 per contact/company **export** (CSV, CRM, extension, API); richer data (technographics, org charts, alerts) costs more.
- Best for: US enterprise/mid-market, buying-group and intent plays. Weak: price, contracts, aggressive renewals.

### 2.2 Cognism (✅ structure; ⚠️ prices)
- EU/UK-leading; "Diamond Data" = phone-verified mobiles; Bombora intent (Pro, ≤12 topics); DNC/TPS screening and GDPR compliance focus.
- **Packages:** Standard (5 seats) / Pro (5 seats, premium mobiles, intent) / CRM Enrichment add-on / Data-as-a-Service. 1 credit per revealed contact.
- **Pricing:** quote-only; ⚠️ ~$15–20k/yr platform + $1.5–2.5k/user; Vendr median ~$32.7k.
- Best for: EMEA cold-calling teams needing compliant mobiles.

### 2.3 Lusha (⚠️ all prices)
- Chrome extension + web app + API; ~280M contacts; strong for individual reps.
- **Plans (monthly):** Free $0/40 credits · Starter ~$49.90 · Pro ~$69.90 · Premium ~$399.90 · Scale custom; annual ~25% off; credit slider changes price.
- **Credit cost:** email 1; phone 5 → **10 as of Aug 2026** (confirm in your dashboard).
- Best for: cheap per-reveal, LinkedIn prospecting. Weak: DB depth vs Apollo, limited sequencing.

### 2.4 RocketReach (⚠️ Sep-2026 snapshot)
- 700M profiles / 60M companies claimed; email + direct dials; Chrome extension; API on Ultimate.
- **Plans:** Free (5 lifetime lookups) · Essentials $19 annual / $39 monthly (email only) · Pro $52 / $79 (adds phones) · Ultimate $115 / $169 (API, Salesforce, org charts, intent). Monthly plans meter lookups (100/250/1,000); annual = unlimited lookups but capped exports (1,200/3,600/20,000 per yr). Team plans from ~$6k/yr.
- Accuracy benchmarks: ~75% email, ~48% direct dial (vendor-run tests). Data fairly static.

### 2.5 Kaspr (⚠️)
- LinkedIn-first Chrome extension (owned by Cognism); free tier; Starter ~$49/user/mo annual ($65 monthly), Business ~$79 ($99); EU-friendly. Good for SDRs living in LinkedIn.

### 2.6 Seamless.AI (⚠️)
- "Real-time search" model; free tier removed/limited; Pro & Enterprise quote-only annual contracts; reputation for hard auto-renew terms. Email + direct dial.

### 2.7 Hunter.io (✅ pricing page)
| Plan | Monthly | Annual (−30%) | Credits/mo | Email accounts |
|---|---|---|---|---|
| Free | $0 | $0 | 50 | 1 |
| Starter | $49 | $34 ($408/yr) | 2,000 | 3 |
| Growth | $149 | $104 ($1,248/yr) | 10,000 | 10 |
| Scale | $299 | $209 ($2,508/yr) | 25,000 | 20 |
| Enterprise | custom | | | |
- Credits: 1 per email found (Domain Search / Email Finder); bulk domain search 1 per up to 10 emails; **0.5 per verification** (Unknown = free, disposable skipped). Same lookup counted once per period. Credits reset monthly, no rollover; annual = all credits upfront.
- Data Platform (API-only bundle example): $6,500 for 1,000 search + 200,000 verification credits over 12 months.
- Also: Discover (company search), Signals, sequences ("Campaigns"), AI assistant, MCP server. Email-only (no phones).

### 2.8 Snov.io (⚠️)
- Starter ~$39/mo (1,000 credits), 25% off annual; email finder + verifier + drip campaigns + CRM-lite; phones via separate token subscription.

### 2.9 Clearbit → HubSpot Breeze Intelligence
- Acquired by HubSpot late 2023; now "Breeze Intelligence", sold via HubSpot credits only. No standalone API pricing. Still a common provider inside Clay waterfalls.

### 2.10 People Data Labs (PDL) (✅ pricing page)
- API-first; Person Enrichment, Person Search, Company APIs; data licensing.
- Free: 100 credits/mo, contact fields obfuscated. Pro: from $98/mo for 350 credits (~$0.28/record, volume discounts, 20% off annual). Enterprise: custom, data feeds, SSO.
- Billing: 200 response = charged, 404 = free. Best for building your own enrichment pipeline.

### 2.11 Clay (✅ pricing page)
- Not a database — an **orchestration/waterfall** layer over 150+ providers (Apollo, PDL, Hunter, Prospeo, Findymail, Datagma, Lusha, Cognism, ZoomInfo via BYO key, etc.) plus AI agent ("Claygent") web research.
| Plan | Price | Actions/mo | Data credits/mo |
|---|---|---|---|
| Free | $0 | 500 | 100 (200-row tables, no phones/CRM) |
| Launch | $185 ($167 annual) | 15,000 | 3,000 (phones, signals, 50k-row tables) |
| Growth | $495 ($446 annual) | 40,000 | 6,000 (CRM auto-sync, warehouse sync, HTTP API, web intent) |
| Enterprise | custom | 200k+ | 100k+ (SSO/SCIM, RBAC, 15-min sync) |
- **Data credits** (from $0.05) buy third-party data; **Actions** (<$0.01) pay for runs/AI/exports. Empty results cost nothing. BYO API key = no data credits, 1 action. Data credits roll over (up to ~1–2 months' worth); actions don't. Unlimited seats on all plans.
- Waterfall cost: pays each step that returns data (even if a later step overrides it) — typical work-email waterfall 4–8 credits. Benchmarks show a 5-provider Clay waterfall reaching ~88% email accuracy, highest in tests.

### 2.12 FullContact
- Identity-resolution API (consumer + B2B), privacy-first; custom pricing only.

### 2.13 Others worth knowing (⚠️ single-source prices)
- **UpLead** — ~$74/mo+, 95% accuracy guarantee, real-time email verification; US-centric.
- **Lead411** — ~$49/mo+, unlimited-ish email plans, intent (Bombora), US.
- **LeadIQ** — ~$200/mo+ (⚠️), capture from LinkedIn, Salesforce-native.
- **Wiza** — ~$49/mo, Sales Navigator export + verification.
- **Prospeo / Findymail / Datagma / LeadMagic / Icypeas** — cheap API email finders ($29–99/mo), common Clay waterfall steps.
- **Dropcontact** — pay-on-success email enrichment, EU-hosted, ~€24–79/mo.
- **ContactOut, SignalHire, GetProspect, Skrapp, Snov** — LinkedIn extension email finders, free tiers.
- **Proxycurl (Nubela)** — LinkedIn profile API, **shut down after LinkedIn lawsuit (2025)**; avoid dependencies on LinkedIn-scraping APIs.

### 2.14 India-focused (⚠️ vendor blogs)
- **Zintlr** — Indian decision-makers from MCA filings + verified mobiles; claims 400M+ global.
- **EasyLeadz** — Delhi-based, INR pricing, direct dials, DPDP-compliant claim, India-only.
- **Pintel.ai** — Tier-2/3 cities, manufacturing/trading; newer.
- **Fundoodata** — oldest Indian B2B company DB (2005), basic emails.
- Apollo's Indian mobile coverage is rated limited by competitors; always trial on your own target list. Check **DPDP Act** and **TRAI DND** rules before cold-calling India.

---

## 3. Side-by-side quick matrix

| Vendor | Entry price | Free tier | Emails | Mobiles | API | Sequencing | Geo strength | Pricing model |
|---|---|---|---|---|---|---|---|---|
| Apollo | ~$49/seat/mo | Yes (generous) | ✔ | ✔ (8 cr) | ✔ (plan-gated) | ✔ | US | Seats + credits |
| ZoomInfo | ~$15k/yr | Trial only | ✔ | ✔ | ✔ | ✔ (Engage) | US | Quote, annual |
| Cognism | ~$15k/yr | No | ✔ | ✔✔ | ✔ | ✘ | EU/UK | Quote |
| Lusha | ~$50/mo | 40 cr/mo | ✔ | ✔ (5–10 cr) | ✔ | Basic | Global | Credits |
| RocketReach | $19–39/mo | 5 lookups | ✔ | Pro+ | Ultimate | Basic | Global | Lookups/exports |
| Kaspr | ~$49/mo | Yes | ✔ | ✔ | ✔ | ✘ | EU | Credits |
| Hunter | $34–49/mo | 50 cr/mo | ✔ | ✘ | ✔ all plans | ✔ | Global | Credits |
| PDL | $98/mo | 100 cr (obfuscated) | ✔ | ✔ | ✔ only | ✘ | Global | Per record |
| Clay | $167–185/mo | 100 data cr | via partners | via partners | ✔ (Growth) | ✔ | n/a | Credits + actions |
| Snov | ~$39/mo | Yes | ✔ | add-on | ✔ | ✔ | Global | Credits |

---

## 4. Legal & compliance notes (not legal advice)
- **GDPR/UK GDPR:** B2B contact data is personal data even if public. Lawful basis is usually *legitimate interests* → documented balancing test, easy opt-out, privacy notice within a month of first contact. Personal emails and mobiles are highest-risk. Apollo blocks personal-email reveals in GDPR regions; Cognism/Kaspr screen DNC lists.
- **CCPA/CPRA:** disclosure + honour deletion/opt-out; "publicly available" exemption is narrower than vendors imply.
- **India DPDP Act 2023 + TRAI DND:** consent-centric; check vendor's basis for Indian mobiles.
- **CAN-SPAM / CASL / PECR:** opt-out + identification in email; PECR (UK) and CASL (Canada) are stricter for individuals.
- **LinkedIn scraping:** hiQ v. LinkedIn (CFAA) was vacated/settled, not binding; LinkedIn enforces via ToS, account bans, and lawsuits (Proxycurl 2025). Prefer licensed vendors over DIY scraping; keep extension usage within normal human rates.
- **Data minimisation:** pull only fields you'll use; set retention; log source + lawful basis per record.

---

## 5. Practical playbooks

**A. Build a list for free, pay only for what you contact**
1. Apollo `api_search` with tight filters (0 credits) → export IDs + `has_email` flag.
2. Enrich only `has_email=true` rows via `/people/match` (1 credit each).
3. Verify with Hunter (0.5 cr) or a bulk verifier; drop "risky/unknown".
4. Load into Apollo sequence or your own sender.

**B. Phone-heavy (SDR calling)**
- EU: Cognism Diamond or Kaspr. US: ZoomInfo or Apollo (expect ~65% phone accuracy). India: Zintlr/EasyLeadz. Or run Clay waterfall: Apollo → Lusha → Cognism → PDL, stop at first hit.

**C. Developer pipeline**
- PDL or Apollo API for enrichment; Hunter/Prospeo for email finding; cache by LinkedIn URL / hashed email; respect per-team rate limits; use webhooks for phones; store `match_confidence`.

**D. Cost sanity (per 1,000 verified work emails, ⚠️ approx.)**
- Apollo Basic: ~1,000 credits ≈ included in 2,500/mo → effectively <$50.
- Hunter Starter: 1,000 credits of 2,000 → ~$25–49.
- PDL Pro: ~$280.
- Clay waterfall: 4–8k data credits ≈ $200–400.
- ZoomInfo/Cognism: bundled in $15k+ contract.

---

## 6. Open items to re-verify (figures that conflicted across sources)
- Apollo per-plan credit allowances and Free-tier email cap (100 vs 1,200/yr vs 10,000/mo).
- Apollo exact plan tier that unlocks API keys (Basic vs Org/Custom).
- Lusha phone credit cost (5 vs 10).
- RocketReach current list prices (promos churn monthly).
- Clay Launch/Growth headline price ($167/185, $446/495 – annual vs monthly).

## 7. Source index
Official: apollo.io/pricing · docs.apollo.io (reference/people-api-search, people-enrichment, bulk-people-enrichment, organization-search, rate-limits) · knowledge.apollo.io "What Are Credits?" · hunter.io/pricing · peopledatalabs.com/pricing · clay.com/pricing · cognism.com/pricing · zoominfo.com/pricing
Third-party (2026): joinvalley.co, salesmotion.io, phantombuster.com, saleshandy.com, scalelist.com, salesquants.com, amplemarket.com, cleanlist.ai, syncgtm.com, emelia.io, overloop.com, zeliq.com, landbase.com, supered.io, salesintel.io, zintlr.com, pintel.ai, coldcast.io, phantombuster.com (legal), iswebscrapinglegal.com
