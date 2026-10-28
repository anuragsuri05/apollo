"""Apollo-compatible filter parsing + serialization."""
from fastapi import Request
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Query, Session

from .config import MAX_PAGES, PAGE_SIZE_MAX
from .models import Organization, Person
from .util import norm_name, norm_person


# ---------- param helpers ----------
async def collect_params(request: Request) -> dict:
    """Merge query string (incl. foo[] arrays), JSON body and form body into one dict of lists."""
    out: dict[str, list] = {}

    def add(k, v):
        k = k[:-2] if k.endswith("[]") else k
        if isinstance(v, list):
            out.setdefault(k, []).extend(str(x) for x in v if x is not None)
        elif v is not None and v != "":
            out.setdefault(k, []).append(str(v))

    for k, v in request.query_params.multi_items():
        add(k, v)
    ctype = request.headers.get("content-type", "")
    if "json" in ctype:
        try:
            body = await request.json()
            if isinstance(body, dict):
                for k, v in body.items():
                    if isinstance(v, dict):  # revenue_range: {min, max}
                        for kk, vv in v.items():
                            add(f"{k}[{kk}]", vv)
                    else:
                        add(k, v)
        except Exception:
            pass
    elif "form" in ctype:
        form = await request.form()
        for k, v in form.multi_items():
            add(k, v)
    return out


def one(p: dict, k: str, default=None):
    v = p.get(k)
    return v[0] if v else default


def many(p: dict, k: str) -> list[str]:
    return [x for x in p.get(k, []) if x]


def paging(p: dict):
    page = max(1, min(int(one(p, "page", 1) or 1), MAX_PAGES))
    per_page = max(1, min(int(one(p, "per_page", 25) or 25), PAGE_SIZE_MAX))
    return page, per_page


def _ilike_any(col, values):
    return or_(*[col.ilike(f"%{v}%") for v in values])


def _location_clause(cols, values):
    return or_(*[or_(*[c.ilike(f"%{part.strip()}%") for c in cols]) for v in values for part in [v]])


# ---------- query builders ----------
def org_filters(q: Query, p: dict) -> Query:
    if v := many(p, "organization_ids"):
        q = q.filter(Organization.id.in_([int(x) for x in v if x.isdigit()]))
    if v := many(p, "q_organization_domains_list"):
        q = q.filter(Organization.domain.in_([x.lower().strip() for x in v]))
    if v := one(p, "q_organization_name"):
        q = q.filter(or_(Organization.name.ilike(f"%{v}%"), Organization.name_norm.ilike(f"%{norm_name(v)}%")))
    if v := many(p, "organization_locations"):
        q = q.filter(_location_clause([Organization.city, Organization.state, Organization.country], v))
    if v := many(p, "organization_not_locations"):
        q = q.filter(~_location_clause([Organization.city, Organization.state, Organization.country], v))
    if v := many(p, "organization_industries"):
        q = q.filter(_ilike_any(Organization.industry, v))
    if v := many(p, "organization_sic_codes"):
        q = q.filter(or_(*[Organization.sic_code.like(f"{x}%") for x in v]))
    if v := many(p, "organization_naics_codes"):
        q = q.filter(or_(*[Organization.naics_code.like(f"{x}%") for x in v]))
    if v := many(p, "organization_num_employees_ranges"):
        clauses = []
        for r in v:
            lo, _, hi = r.partition(",")
            c = [Organization.employee_count >= int(lo or 0)]
            if hi:
                c.append(Organization.employee_count <= int(hi))
            clauses.append(and_(*c))
        q = q.filter(or_(*clauses))
    if v := one(p, "revenue_range[min]"):
        q = q.filter(Organization.revenue >= float(v))
    if v := one(p, "revenue_range[max]"):
        q = q.filter(Organization.revenue <= float(v))
    if v := many(p, "organization_sources"):
        q = q.filter(Organization.source.in_(v))
    if v := many(p, "q_organization_keyword_tags"):
        q = q.filter(or_(_ilike_any(Organization.description, v), _ilike_any(Organization.industry, v), _ilike_any(Organization.name, v)))
    if one(p, "has_domain") in ("true", "1"):
        q = q.filter(Organization.domain.isnot(None))
    return q


def people_query(db: Session, p: dict) -> Query:
    q = db.query(Person).outerjoin(Organization, Person.organization_id == Organization.id)
    if v := many(p, "person_titles"):
        q = q.filter(_ilike_any(Person.title, v))
    if v := many(p, "person_not_titles"):
        q = q.filter(or_(Person.title.is_(None), ~_ilike_any(Person.title, v)))
    if v := many(p, "person_seniorities"):
        q = q.filter(Person.seniority.in_(v))
    if v := many(p, "person_departments"):
        q = q.filter(Person.department.in_(v))
    if v := many(p, "person_locations"):
        q = q.filter(or_(_location_clause([Person.city, Person.state, Person.country], v),
                         _location_clause([Organization.city, Organization.state, Organization.country], v)))
    if v := many(p, "person_not_locations"):
        q = q.filter(~_location_clause([Person.city, Person.state, Person.country], v))
    if v := one(p, "q_person_name"):
        q = q.filter(or_(Person.full_name.ilike(f"%{v}%"), Person.name_norm.ilike(f"%{norm_person(v)}%")))
    if v := one(p, "q_keywords"):
        q = q.filter(or_(Person.title.ilike(f"%{v}%"), Person.full_name.ilike(f"%{v}%"), Organization.name.ilike(f"%{v}%"), Organization.industry.ilike(f"%{v}%")))
    if v := many(p, "contact_email_status"):
        q = q.filter(Person.email_status.in_(v))
    if v := many(p, "person_sources"):
        q = q.filter(Person.source.in_(v))
    if one(p, "has_email") in ("true", "1"):
        q = q.filter(Person.email.isnot(None))
    # organisation-level filters apply through the join
    org_keys = [k for k in p if k.startswith("organization_") or k.startswith("q_organization") or k.startswith("revenue_range")]
    if org_keys:
        q = org_filters(q, p)
    return q


# ---------- serialization ----------
def org_dict(o: Organization | None, full: bool = True) -> dict | None:
    if not o:
        return None
    d = {
        "id": o.id, "name": o.name, "domain": o.domain, "website_url": o.website,
        "linkedin_url": o.linkedin_url, "industry": o.industry, "estimated_num_employees": o.employee_count,
        "country": o.country, "state": o.state, "city": o.city,
    }
    if full:
        d.update({
            "sic_code": o.sic_code, "naics_code": o.naics_code, "annual_revenue": o.revenue,
            "founded_year": o.founded_year, "address": o.address, "postal_code": o.postal_code,
            "phone": o.phone, "short_description": o.description, "lei": o.lei, "ticker": o.ticker,
            "exchange": o.exchange, "cik": o.cik, "company_number": o.company_number, "status": o.status,
            "email_pattern": o.email_pattern, "mx_valid": o.mx_valid, "source": o.source, "source_url": o.source_url,
        })
    return d


def person_dict(p: Person, reveal: bool = False) -> dict:
    org = p.organization
    d = {
        "id": p.id, "first_name": p.first_name, "last_name": p.last_name, "name": p.full_name,
        "title": p.title, "seniority": p.seniority, "department": p.department,
        "linkedin_url": p.linkedin_url, "city": p.city, "state": p.state, "country": p.country,
        "has_email": bool(p.email) or bool(org and org.domain),
        "email_status": p.email_status if p.email else ("guessable" if org and org.domain else "unavailable"),
        "has_direct_phone": bool(p.phone),
        "organization_name": org.name if org else p.organization_name,
        "organization": org_dict(org, full=False),
        "source": p.source, "source_url": p.source_url,
    }
    if reveal:
        d["email"] = p.email
        d["phone_numbers"] = [{"raw_number": p.phone, "type": "work"}] if p.phone else []
    return d


def pagination(page, per_page, total):
    return {"page": page, "per_page": per_page, "total_entries": total,
            "total_pages": min(MAX_PAGES, (total + per_page - 1) // per_page)}
