from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import current_user, master_user
from ..config import PLANS
from ..credits import balance
from ..db import get_db
from ..models import ApiUsage, CreditLedger, IngestRun, Organization, Person, User

router = APIRouter(prefix="/api/v1", tags=["usage"])


@router.get("/usage_stats/api_usage_stats")
def api_usage(user: User = Depends(master_user), db: Session = Depends(get_db)):
    plan = PLANS.get(user.plan, PLANS["free"])
    since = datetime.utcnow() - timedelta(days=1)
    rows = db.query(ApiUsage.endpoint, func.count(ApiUsage.id)).filter(ApiUsage.user_id == user.id, ApiUsage.created_at >= since).group_by(ApiUsage.endpoint).all()
    return {"plan": user.plan, "limits": {"per_minute": plan["rate_per_minute"], "per_hour": None, "per_day": None},
            "usage_last_24h": {e: n for e, n in rows}}


@router.get("/usage_stats/credit_usage")
def credit_usage(user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = balance(db, user)
    by_action = db.query(CreditLedger.action, func.sum(CreditLedger.amount)).filter(CreditLedger.user_id == user.id).group_by(CreditLedger.action).all()
    b["by_action"] = {a: int(n) for a, n in by_action}
    return b


@router.get("/stats")
def db_stats(db: Session = Depends(get_db)):
    """Public dashboard numbers: how big is the library right now."""
    people = db.query(func.count(Person.id)).scalar()
    orgs = db.query(func.count(Organization.id)).scalar()
    with_email = db.query(func.count(Person.id)).filter(Person.email.isnot(None)).scalar()
    with_domain = db.query(func.count(Organization.id)).filter(Organization.domain.isnot(None)).scalar()
    by_src_p = db.query(Person.source, func.count(Person.id)).group_by(Person.source).all()
    by_src_o = db.query(Organization.source, func.count(Organization.id)).group_by(Organization.source).all()
    by_country = db.query(Organization.country, func.count(Organization.id)).group_by(Organization.country).order_by(func.count(Organization.id).desc()).limit(15).all()
    by_status = db.query(Person.email_status, func.count(Person.id)).group_by(Person.email_status).all()
    runs = db.query(IngestRun).order_by(IngestRun.id.desc()).limit(20).all()
    return {
        "people": people, "organizations": orgs, "people_with_email": with_email, "orgs_with_domain": with_domain,
        "people_by_source": dict(by_src_p), "orgs_by_source": dict(by_src_o),
        "orgs_by_country": [{"country": c or "?", "n": n} for c, n in by_country],
        "email_status": dict(by_status),
        "ingest_runs": [{"id": r.id, "source": r.source, "args": r.args, "status": r.status, "rows_in": r.rows_in,
                         "orgs": r.orgs_upserted, "people": r.people_upserted, "started": r.started_at, "finished": r.finished_at, "error": r.error} for r in runs],
    }
