from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from ..auth import create_api_key, create_session, current_user, hash_password, verify_password
from ..credits import balance
from ..db import get_db
from ..models import ApiKey, User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class Creds(BaseModel):
    email: str
    password: str
    name: str = ""

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("invalid email")
        return v


class KeyReq(BaseModel):
    label: str = "default"
    is_master: bool = False


def _set_cookie(resp: Response, token: str):
    resp.set_cookie("gc_session", token, httponly=True, samesite="lax", max_age=30 * 86400)


@router.post("/signup")
def signup(c: Creds, resp: Response, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == c.email.lower()).first():
        raise HTTPException(409, {"error": "email_taken"})
    if len(c.password) < 8:
        raise HTTPException(422, {"error": "password_too_short"})
    u = User(email=c.email.lower(), name=c.name, password_hash=hash_password(c.password))
    db.add(u)
    db.commit()
    u.team_id = u.id
    db.commit()
    raw = create_api_key(db, u, "default", is_master=True)
    token = create_session(db, u)
    _set_cookie(resp, token)
    return {"user": {"id": u.id, "email": u.email, "name": u.name, "plan": u.plan}, "session_token": token, "api_key": raw}


@router.post("/login")
def login(c: Creds, resp: Response, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == c.email.lower()).first()
    if not u or not verify_password(c.password, u.password_hash):
        raise HTTPException(401, {"error": "bad_credentials"})
    token = create_session(db, u)
    _set_cookie(resp, token)
    return {"user": {"id": u.id, "email": u.email, "name": u.name, "plan": u.plan}, "session_token": token}


@router.post("/logout")
def logout(resp: Response):
    resp.delete_cookie("gc_session")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"user": {"id": user.id, "email": user.email, "name": user.name, "plan": user.plan}, "credits": balance(db, user)}


@router.get("/api_keys")
def list_keys(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(ApiKey).filter(ApiKey.user_id == user.id).all()
    return {"api_keys": [{"id": k.id, "prefix": k.prefix + "…", "label": k.label, "is_master": k.is_master,
                          "created_at": k.created_at, "last_used_at": k.last_used_at} for k in rows]}


@router.post("/api_keys")
def new_key(r: KeyReq, user: User = Depends(current_user), db: Session = Depends(get_db)):
    raw = create_api_key(db, user, r.label, r.is_master)
    return {"api_key": raw, "label": r.label, "is_master": r.is_master, "note": "store it now; it is not shown again"}


@router.delete("/api_keys/{key_id}")
def del_key(key_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    k = db.get(ApiKey, key_id)
    if not k or k.user_id != user.id:
        raise HTTPException(404)
    db.delete(k)
    db.commit()
    return {"ok": True}
