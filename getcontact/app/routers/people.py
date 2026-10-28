from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import current_user
from ..credits import charge
from ..db import get_db
from ..email_engine import guess_email, learn_pattern
from ..models import Contact, Organization, Person, Suppression, User
from ..search import collect_params, many, one, paging, pagination, people_query, person_dict, org_dict
from ..util import domain_from_url, norm_name, norm_person, split_name, infer_seniority, infer_department

router = APIRouter(prefix="/api/v1", tags=["people"])


# ---------------- search (0 credits, no emails) ----------------
@router.api_route("/mixed_people/api_search", methods=["GET", "POST"])
async def people_search(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = await collect_params(request)
    page, per_page = paging(p)
    q = people_query(db, p)
    total = q.count()
    rows = q.order_by(Person.id).offset((page - 1) * per_page).limit(per_page).all()
    return {"people": [person_dict(r) for r in rows], "pagination": pagination(page, per_page, total),
            "credits_consumed": 0}


# ---------------- enrichment ----------------
def _resolve_org(db: Session, domain: str | None, name: str | None) -> Organization | None:
    if domain:
        o = db.query(Organization).filter(Organization.domain == domain.lower()).first()
        if o:
            return o
    if name:
        o = db.query(Organization).filter(Organization.name_norm == norm_name(name)).first()
        if o:
            return o
        o = db.query(Organization).filter(Organization.name.ilike(f"%{name}%")).order_by(Organization.employee_count.desc().nullslast()).first()
        if o:
            return o
    return None


def _find_person(db: Session, p: dict):
    conf = "none"
    if v := one(p, "id"):
        per = db.get(Person, int(v))
        return per, ("high" if per else "none")
    if v := one(p, "linkedin_url"):
        v = v.rstrip("/").lower().replace("http://", "https://").replace("https://www.", "https://")
        per = db.query(Person).filter(Person.linkedin_url.ilike(f"%{v.split('linkedin.com')[-1]}%")).first()
        if per:
            return per, "high"
    if v := one(p, "email"):
        per = db.query(Person).filter(Person.email == v.lower()).first()
        if per:
            return per, "high"
    first, last = one(p, "first_name", ""), one(p, "last_name", "")
    name = one(p, "name") or f"{first} {last}".strip()
    if not name:
        return None, conf
    domain = one(p, "domain") or domain_from_url(one(p, "email", "").split("@")[-1] if one(p, "email") else None)
    org = _resolve_org(db, domain, one(p, "organization_name"))
    q = db.query(Person).filter(Person.name_norm == norm_person(name))
    if org:
        rows = q.filter(Person.organization_id == org.id).all()
        if rows:
            return rows[0], "high"
    rows = q.limit(3).all()
    if len(rows) == 1:
        return rows[0], "medium" if not org else "low"
    if rows:
        return rows[0], "low"
    return None, "none"


def _enrich_one(db: Session, user: User, p: dict, reveal_phone: bool) -> dict:
    per, conf = _find_person(db, p)
    credits = 0
    first, last = one(p, "first_name", ""), one(p, "last_name", "")
    if not (first or last) and one(p, "name"):
        first, last = split_name(one(p, "name"))
    domain = (one(p, "domain") or "").lower() or None
    org = per.organization if per else _resolve_org(db, domain, one(p, "organization_name"))
    if per is None:
        # synthesize from name + domain (Hunter-style email finder)
        if not (first or last) or not (domain or (org and org.domain)):
            return {"person": None, "match_confidence": "none", "credits_consumed": 0}
        d = domain or org.domain
        email, status, score = guess_email(db, first, last, d)
        if email and db.get(Suppression, email):
            email, status, score = None, "suppressed", 0.0
        if email and status != "invalid":
            credits += charge(db, user, "email", ref=f"guess:{email}")
        return {"person": {"first_name": first, "last_name": last, "name": f"{first} {last}".strip(),
                           "email": email, "email_status": status, "email_confidence": score,
                           "organization": org_dict(org)}, "match_confidence": "low", "credits_consumed": credits}

    if not per.email and per.email_status != "suppressed" and org and org.domain:
        email, status, score = guess_email(db, per.first_name, per.last_name, org.domain)
        if email and status != "invalid" and not db.get(Suppression, email):
            per.email, per.email_status = email, status
            db.commit()
    d = person_dict(per, reveal=True)
    d["contributors"] = per.contributors or 0
    d["last_seen_at"] = per.last_seen_at
    d["last_verified_at"] = per.last_verified_at
    if per.email and per.email_status != "invalid":
        credits += charge(db, user, "email", ref=f"person:{per.id}")
        if per.email_status == "verified":
            learn_pattern(db, org.domain if org else per.email.split("@")[1], per.first_name, per.last_name, per.email)
    if reveal_phone and per.phone:
        credits += charge(db, user, "phone", ref=f"person:{per.id}")
    else:
        d["phone_numbers"] = []
    # save into workspace as a Contact (Apollo auto-saves revealed people)
    c = db.query(Contact).filter(Contact.user_id == user.id, Contact.person_id == per.id).first()
    if not c:
        c = Contact(user_id=user.id, person_id=per.id, first_name=per.first_name, last_name=per.last_name,
                    title=per.title, organization_name=org.name if org else per.organization_name,
                    linkedin_url=per.linkedin_url)
        db.add(c)
    c.email, c.email_status = per.email, per.email_status
    if reveal_phone:
        c.phone = per.phone
    db.commit()
    d["contact_id"] = c.id
    d["organization"] = org_dict(org)
    return {"person": d, "match_confidence": conf, "credits_consumed": credits}


@router.api_route("/people/match", methods=["GET", "POST"])
async def people_match(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = await collect_params(request)
    reveal_phone = one(p, "reveal_phone_number", "false").lower() in ("true", "1")
    return _enrich_one(db, user, p, reveal_phone)


@router.post("/people/bulk_match")
async def people_bulk_match(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    body = await request.json()
    details = body.get("details") or []
    if not isinstance(details, list) or not details:
        raise HTTPException(422, {"error": "details[] required"})
    if len(details) > 10:
        raise HTTPException(422, {"error": "max 10 people per call"})
    reveal_phone = str(request.query_params.get("reveal_phone_number", body.get("reveal_phone_number", "false"))).lower() in ("true", "1")
    matches, total = [], 0
    for d in details:
        p = {k: [str(v)] for k, v in d.items() if v not in (None, "")}
        r = _enrich_one(db, user, p, reveal_phone)
        total += r["credits_consumed"]
        matches.append(r["person"])
    return {"status": "success", "total_requested_enrichments": len(details),
            "unique_enriched_records": sum(1 for m in matches if m), "missing_records": sum(1 for m in matches if not m),
            "credits_consumed": total, "matches": matches}


@router.get("/people/{person_id}")
def get_person(person_id: int, reveal: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
    per = db.get(Person, person_id)
    if not per:
        raise HTTPException(404)
    if reveal:
        return _enrich_one(db, user, {"id": [str(person_id)]}, reveal_phone=True)
    return {"person": person_dict(per), "organization": org_dict(per.organization)}


# ---------------- manual add (for extension / CSV) ----------------
@router.post("/people")
async def add_person(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = await request.json()
    first, last = b.get("first_name", ""), b.get("last_name", "")
    if not (first or last) and b.get("name"):
        first, last = split_name(b["name"])
    domain = b.get("domain") or domain_from_url(b.get("website"))
    org = _resolve_org(db, domain, b.get("organization_name"))
    if not org and (domain or b.get("organization_name")):
        org = Organization(name=b.get("organization_name") or domain, name_norm=norm_name(b.get("organization_name") or domain),
                           domain=domain, source="user", source_id=f"u{user.id}:{domain or b.get('organization_name')}")
        db.add(org)
        db.flush()
    sid = f"u{user.id}:{norm_person(first + ' ' + last)}:{org.id if org else ''}"
    per = db.query(Person).filter(Person.source == "user", Person.source_id == sid).first()
    if not per:
        per = Person(source="user", source_id=sid)
        db.add(per)
    per.first_name, per.last_name, per.full_name = first, last, f"{first} {last}".strip()
    per.name_norm = norm_person(per.full_name)
    per.title = b.get("title") or per.title
    per.seniority, per.department = infer_seniority(per.title), infer_department(per.title)
    per.organization_id = org.id if org else None
    per.organization_name = org.name if org else b.get("organization_name")
    per.linkedin_url = b.get("linkedin_url") or per.linkedin_url
    per.city, per.state, per.country = b.get("city") or per.city, b.get("state") or per.state, b.get("country") or per.country
    if b.get("email"):
        per.email, per.email_status = b["email"].lower(), b.get("email_status", "verified")
        learn_pattern(db, per.email.split("@")[1], first, last, per.email)
    db.commit()
    return {"person": person_dict(per, reveal=True)}
