"""Generic CSV import. Header names are matched case-insensitively against common aliases.

    python -m ingest.run csv --file leads.csv --source-name my_crm
Recognised person columns:  first_name, last_name, name/full_name, title/job_title/position, email, phone, linkedin/linkedin_url, city, state, country
Recognised company columns: company/organization/company_name, domain/website, industry, employees/employee_count, company_country
"""
import csv as _csv

ALIASES = {
    "first_name": ["first_name", "firstname", "first"], "last_name": ["last_name", "lastname", "last", "surname"],
    "name": ["name", "full_name", "fullname", "contact"], "title": ["title", "job_title", "position", "role", "designation"],
    "email": ["email", "email_address", "work_email"], "phone": ["phone", "mobile", "phone_number", "direct_dial"],
    "linkedin_url": ["linkedin", "linkedin_url", "profile"], "city": ["city"], "state": ["state", "region"], "country": ["country"],
    "company": ["company", "organization", "organisation", "company_name", "employer", "account"],
    "domain": ["domain", "website", "company_domain", "url"], "industry": ["industry", "sector"],
    "employees": ["employees", "employee_count", "headcount", "size"], "company_country": ["company_country", "hq_country"],
}


def add_args(p):
    p.add_argument("--file", required=True)
    p.add_argument("--source-name", default="csv")
    p.add_argument("--email-status", default="verified", help="status to assign to imported emails")


def run(ing, args):
    ing.source = args.source_name
    with open(args.file, newline="", encoding="utf-8-sig") as f:
        rd = _csv.DictReader(f)
        cols = {c.lower().strip(): c for c in rd.fieldnames or []}
        m = {}
        for key, al in ALIASES.items():
            for a in al:
                if a in cols:
                    m[key] = cols[a]
                    break

        def g(row, k):
            return (row.get(m[k]) or "").strip() if k in m else ""

        n = 0
        for row in rd:
            comp, dom = g(row, "company"), g(row, "domain")
            org = None
            if comp or dom:
                emp = g(row, "employees")
                org = ing.upsert_org(comp or dom, dom or comp.lower(), domain=dom or None, website=dom or None, industry=g(row, "industry") or None,
                                     employee_count=int(emp) if emp.isdigit() else None, country=g(row, "company_country") or None)
            first, last, name = g(row, "first_name"), g(row, "last_name"), g(row, "name")
            full = name or f"{first} {last}".strip()
            if full:
                email = g(row, "email") or None
                ing.upsert_person(full, email or f"{full.lower()}@{(org.name_norm if org else 'none')}", org, first_name=first or None, last_name=last or None,
                                  title=g(row, "title") or None, email=email, email_status=args.email_status, phone=g(row, "phone") or None,
                                  linkedin_url=g(row, "linkedin_url") or None, city=g(row, "city") or None, state=g(row, "state") or None,
                                  country=g(row, "country") or None, force=True)
            n += 1
            if n % 2000 == 0:
                ing.commit()
                ing.progress()
            if args.limit and n >= args.limit:
                break
    ing.commit()
