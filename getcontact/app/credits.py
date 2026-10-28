from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .config import CREDIT_COST, PLANS
from .models import CreditLedger, User


def month_start():
    n = datetime.utcnow()
    return n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def used_this_month(db: Session, user: User) -> int:
    q = db.query(func.coalesce(func.sum(CreditLedger.amount), 0)).filter(
        CreditLedger.user_id == user.id, CreditLedger.created_at >= month_start()
    )
    return int(q.scalar() or 0)


def balance(db: Session, user: User) -> dict:
    plan = PLANS.get(user.plan, PLANS["free"])
    used = used_this_month(db, user)
    return {"plan": user.plan, "credits_per_month": plan["credits_per_month"], "used": used,
            "remaining": max(plan["credits_per_month"] - used, 0), "costs": CREDIT_COST}


def charge(db: Session, user: User, action: str, ref: str = "", amount: int | None = None) -> int:
    amt = CREDIT_COST[action] if amount is None else amount
    if amt <= 0:
        return 0
    plan = PLANS.get(user.plan, PLANS["free"])
    if used_this_month(db, user) + amt > plan["credits_per_month"]:
        raise HTTPException(402, {"error": "insufficient_credits"})
    db.add(CreditLedger(user_id=user.id, action=action, amount=amt, ref=ref))
    db.commit()
    return amt
