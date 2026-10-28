from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..email_engine import mx_valid, pattern_for_domain
from ..models import Organization, Person, User
from ..search import collect_params, one, org_dict, org_filters, paging, pagination, person_dict
from ..util import norm_name

router = APIRouter(prefix="/api/v1", tags=["organizations"])


@router.api_route("/mixed_companies/search", methods=["GET", "POST"])
async def org_search(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = await collect_params(request)
    page, per_page = paging(p)
    q = org_filters(db.query(Organization), p)
    total = q.count()
    rows = q.order_by(Organization.employee_count.desc().nullslast(), Organization.id).offset((page - 1) * per_page).limit(per_page).all()
    ids = [r.id for r in rows]
    counts = dict(db.query(Person.organization_id, func.count(Person.id)).filter(Person.organization_id.in_(ids)).group_by(Person.organization_id).all()) if ids else {}
    out = []
    for r in rows:
        d = org_dict(r)
        d["num_people"] = counts.get(r.id, 0)
        out.append(d)
    return {"organizations": out, "pagination": pagination(page, per_page, total), "credits_consumed": 0}


@router.api_route("/organizations/enrich", methods=["GET", "POST"])
async def org_enrich(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = await collect_params(request)
    domain = (one(p, "domain") or "").lower().replace("www.", "")
    name = one(p, "name")
    o = None
    if domain:
        o = db.query(Organization).filter(Organization.domain == domain).first()
    if not o and name:
        o = db.query(Organization).filter(Organization.name_norm == norm_name(name)).first()
    if not o:
        if not domain:
            raise HTTPException(404, {"error": "not_found"})
        pat, conf = pattern_for_domain(db, domain)
        return {"organization": {"domain": domain, "name": None, "mx_valid": mx_valid(domain), "email_pattern": pat,
                                 "email_pattern_confidence": conf}, "match_confidence": "none"}
    d = org_dict(o)
    if o.domain and o.mx_valid is None:
        o.mx_valid = mx_valid(o.domain)
        db.commit()
        d["mx_valid"] = o.mx_valid
    pat, conf = pattern_for_domain(db, o.domain) if o.domain else (None, 0)
    d["email_pattern"], d["email_pattern_confidence"] = o.email_pattern or pat, conf
    d["num_people"] = db.query(func.count(Person.id)).filter(Person.organization_id == o.id).scalar()
    return {"organization": d, "match_confidence": "high"}


@router.get("/organizations/{org_id}")
def get_org(org_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    o = db.get(Organization, org_id)
    if not o:
        raise HTTPException(404)
    d = org_dict(o)
    d["num_people"] = db.query(func.count(Person.id)).filter(Person.organization_id == o.id).scalar()
    return {"organization": d}


@router.get("/organizations/{org_id}/people")
def org_people(org_id: int, page: int = 1, per_page: int = 25, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Person).filter(Person.organization_id == org_id)
    total = q.count()
    rows = q.order_by(Person.id).offset((page - 1) * per_page).limit(min(per_page, 100)).all()
    return {"people": [person_dict(r) for r in rows], "pagination": pagination(page, per_page, total)}
