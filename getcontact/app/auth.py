import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as OrmSession

from .config import PLANS
from .db import get_db
from .models import ApiKey, Session, User, ApiUsage


# ---------- passwords ----------
def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000)
    return f"{salt}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        salt, hexdk = stored.split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000)
    return hmac.compare_digest(dk.hex(), hexdk)


# ---------- sessions & api keys ----------
def create_session(db: OrmSession, user: User, days: int = 30) -> str:
    token = secrets.token_urlsafe(32)
    db.add(Session(token=token, user_id=user.id, expires_at=datetime.utcnow() + timedelta(days=days)))
    db.commit()
    return token


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_api_key(db: OrmSession, user: User, label: str = "default", is_master: bool = False) -> str:
    raw = "gc_" + secrets.token_urlsafe(30)
    db.add(ApiKey(user_id=user.id, key_hash=_hash_key(raw), prefix=raw[:10], label=label, is_master=is_master))
    db.commit()
    return raw


# ---------- rate limiting (per team, fixed windows, Apollo-style headers) ----------
_windows: dict[tuple, deque] = defaultdict(deque)


def _group(path: str) -> str:
    if "/api_search" in path or "/mixed_companies/search" in path:
        return "search"
    if "/match" in path or "/enrich" in path:
        return "enrich"
    return "general"


def rate_limit(request: Request, user: User):
    plan = PLANS.get(user.plan, PLANS["free"])
    limit = plan["rate_per_minute"]
    key = (user.team_id or user.id, _group(request.url.path))
    now = time.time()
    dq = _windows[key]
    while dq and dq[0] < now - 60:
        dq.popleft()
    if len(dq) >= limit:
        retry = int(60 - (now - dq[0])) + 1
        raise HTTPException(429, detail={"error": "rate_limit_exceeded", "retry_after": retry},
                            headers={"retry-after": str(retry)})
    dq.append(now)
    request.state.rl_headers = {
        "x-rate-limit-minute": str(limit),
        "x-minute-usage": str(len(dq)),
        "x-minute-requests-left": str(limit - len(dq)),
    }


# ---------- dependencies ----------
def _resolve(request: Request, db: OrmSession):
    raw = request.headers.get("x-api-key")
    if raw:
        k = db.query(ApiKey).filter(ApiKey.key_hash == _hash_key(raw)).first()
        if not k:
            raise HTTPException(401, {"error": "invalid_api_key"})
        k.last_used_at = datetime.utcnow()
        user = db.get(User, k.user_id)
        return user, k
    token = None
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    token = token or request.cookies.get("gc_session")
    if token:
        s = db.get(Session, token)
        if s and s.expires_at > datetime.utcnow():
            return db.get(User, s.user_id), None
    raise HTTPException(401, {"error": "unauthorized", "hint": "send x-api-key header or log in"})


def current_user(request: Request, db: OrmSession = Depends(get_db)) -> User:
    user, key = _resolve(request, db)
    request.state.api_key = key
    rate_limit(request, user)
    db.add(ApiUsage(user_id=user.id, endpoint=request.url.path))
    db.commit()
    return user


def master_user(request: Request, db: OrmSession = Depends(get_db)) -> User:
    user, key = _resolve(request, db)
    if key is not None and not key.is_master:
        raise HTTPException(403, {"error": "master_api_key_required"})
    request.state.api_key = key
    rate_limit(request, user)
    return user
