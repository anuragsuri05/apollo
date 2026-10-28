"""Contributor network endpoints + opt-out."""
import csv
import io
import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import current_user
from ..contrib import ContribStats, contribute_contact, suppress
from ..db import get_db
from ..mail_sync import import_eml_bytes, import_mbox, seal, sync_account
from ..models import Contribution, MailAccount, Person, Signal, Suppression, User

router = APIRouter(prefix="/api/v1", tags=["contribute"])

CSV_ALIASES = {
    "first": ["first_name", "firstname", "first", "first name", "given name"], "last": ["last_name", "lastname", "last", "surname", "last name", "family name"],
    "name": ["name", "full_name", "full name", "contact", "display name"], "email": ["email", "email_address", "work_email", "e-mail 1 - value", "e-mail address", "email address", "primary email", "e-mail"],
    "title": ["title", "job_title", "job title", "position", "role", "designation", "organization 1 - title", "organization title"],
    "phone": ["phone", "mobile", "phone_number", "direct_dial", "phone 1 - value", "mobile phone", "business phone", "primary phone", "work phone"],
    "company": ["company", "organization", "organisation", "company_name", "employer", "organization 1 - name", "organization name", "account name"],
    "linkedin": ["linkedin", "linkedin_url", "linkedin url", "profile"],
}


class ConsentIn(BaseModel):
    contribute: bool


class AccountIn(BaseModel):
    kind: str = "imap"          # imap | hubspot
    label: str = ""
    host: str | None = None
    port: int = 993
    username: str | None = None
    secret: str                 # IMAP password / app password, or HubSpot private-app token
    use_ssl: bool = True
    folder: str = "INBOX"
    contribute: bool = True
    is_sender: bool = False


class OptOutIn(BaseModel):
    email: str
    reason: str = "optout"


def acct_dict(a: MailAccount):
    return {"id": a.id, "kind": a.kind, "label": a.label, "host": a.host, "port": a.port, "username": a.username, "folder": a.folder,
            "contribute": a.contribute, "is_sender": a.is_sender, "status": a.status, "error": a.error, "last_sync_at": a.last_sync_at,
            "messages_seen": a.messages_seen, "last_uid": a.last_uid}


@router.post("/contribute/consent")
def consent(c: ConsentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.contribute = c.contribute
    db.commit()
    return {"contribute": user.contribute}


@router.get("/contribute/stats")
def stats(user: User = Depends(current_user), db: Session = Depends(get_db)):
    mine = db.query(func.coalesce(func.sum(Contribution.people_added), 0), func.coalesce(func.sum(Contribution.people_updated), 0),
                    func.coalesce(func.sum(Contribution.messages), 0), func.coalesce(func.sum(Contribution.orgs_added), 0)).filter(Contribution.user_id == user.id).first()
    network = db.query(func.count(Person.id)).filter(Person.source.in_(("contributor", "imap", "mbox", "eml", "csv", "hubspot", "extension", "auto_reply"))).scalar()
    verified = db.query(func.count(Person.id)).filter(Person.email_status == "verified").scalar()
    recent = db.query(Contribution).filter(Contribution.user_id == user.id).order_by(Contribution.id.desc()).limit(20).all()
    return {"contribute": user.contribute, "my": {"people_added": int(mine[0]), "people_updated": int(mine[1]), "messages": int(mine[2]), "orgs_added": int(mine[3])},
            "network": {"contributed_people": network, "verified_emails": verified, "suppressed": db.query(func.count(Suppression.email)).scalar()},
            "recent": [{"id": r.id, "source": r.source, "messages": r.messages, "people_added": r.people_added, "people_updated": r.people_updated, "at": r.created_at} for r in recent]}


@router.get("/mail_accounts")
def list_accounts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"accounts": [acct_dict(a) for a in db.query(MailAccount).filter(MailAccount.user_id == user.id).all()]}


@router.post("/mail_accounts")
def add_account(a: AccountIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if a.kind == "imap" and not (a.host and a.username):
        raise HTTPException(422, {"error": "host and username required for imap"})
    row = MailAccount(user_id=user.id, kind=a.kind, label=a.label or (a.username or a.kind), host=a.host, port=a.port, username=a.username,
                      secret=seal(a.secret), use_ssl=a.use_ssl, folder=a.folder, contribute=a.contribute, is_sender=a.is_sender)
    db.add(row)
    db.commit()
    return {"account": acct_dict(row)}


@router.post("/mail_accounts/{aid}/sync")
def sync_now(aid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    a = db.get(MailAccount, aid)
    if not a or a.user_id != user.id:
        raise HTTPException(404)
    r = sync_account(db, a)
    return {"result": r, "account": acct_dict(a)}


@router.delete("/mail_accounts/{aid}")
def del_account(aid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    a = db.get(MailAccount, aid)
    if not a or a.user_id != user.id:
        raise HTTPException(404)
    db.delete(a)
    db.commit()
    return {"ok": True}


@router.post("/contribute/upload")
async def upload(file: UploadFile = File(...), kind: str = Form("auto"), watch: bool = Form(False), user: User = Depends(current_user), db: Session = Depends(get_db)):
    """MBOX (Google Takeout / Thunderbird / Apple Mail export), a single .eml, or a contacts CSV (Google/Outlook/LinkedIn/CRM export)."""
    name = (file.filename or "").lower()
    k = kind if kind != "auto" else ("csv" if name.endswith(".csv") else "eml" if name.endswith(".eml") else "mbox")
    if k == "csv":
        data = (await file.read()).decode("utf-8-sig", "replace")
        rd = csv.DictReader(io.StringIO(data))
        cols = {c.lower().strip(): c for c in rd.fieldnames or []}
        m = {}
        for key, al in CSV_ALIASES.items():
            for a in al:
                if a in cols:
                    m[key] = cols[a]
                    break
        if "email" not in m:
            raise HTTPException(422, {"error": "no email column found", "columns": list(cols)})
        st = ContribStats()
        g = lambda row, key: (row.get(m[key]) or "").strip() if key in m else ""  # noqa: E731
        for row in rd:
            st.messages += 1
            display = g(row, "name") or f"{g(row, 'first')} {g(row, 'last')}".strip()
            contribute_contact(db, user, display, g(row, "email"), title=g(row, "title") or None, phone=g(row, "phone") or None,
                               source="csv", stats=st, linkedin_url=g(row, "linkedin") or None, company_name=g(row, "company") or None)
            if st.messages % 500 == 0:
                db.commit()
        db.add(Contribution(user_id=user.id, source="csv", **{kk: v for kk, v in st.as_dict().items() if kk != "skipped"}))
        db.commit()
        return {"kind": "csv", **st.as_dict(), "note": "" if user.contribute else "consent is off: nothing was contributed (turn it on under Contribute)"}
    if not user.contribute and not watch:
        raise HTTPException(409, {"error": "consent_required", "hint": "turn on 'contribute my contacts' first"})
    if k == "eml":
        return {"kind": "eml", **import_eml_bytes(db, user, await file.read(), watch=watch)}
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mbox") as tmp:
        while chunk := await file.read(1 << 20):
            tmp.write(chunk)
        path = tmp.name
    try:
        return {"kind": "mbox", **import_mbox(db, user, path, watch=watch)}
    finally:
        os.remove(path)


@router.get("/signals")
def signals(kind: str = "", limit: int = 200, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Signal).filter((Signal.user_id == user.id) | (Signal.user_id.is_(None)))
    if kind:
        q = q.filter(Signal.kind == kind)
    rows = q.order_by(Signal.id.desc()).limit(min(limit, 500)).all()
    counts = dict(db.query(Signal.kind, func.count(Signal.id)).filter(Signal.user_id == user.id).group_by(Signal.kind).all())
    return {"signals": [{"id": s.id, "kind": s.kind, "email": s.email, "person_id": s.person_id, "detail": s.detail, "at": s.created_at} for s in rows], "counts": counts}


# ---------- opt-out (public) ----------
@router.post("/optout")
def optout(o: OptOutIn, db: Session = Depends(get_db)):
    if "@" not in o.email:
        raise HTTPException(422)
    suppress(db, o.email, o.reason[:100])
    return {"suppressed": o.email.lower()}


@router.get("/optout", response_class=HTMLResponse, include_in_schema=False)
def optout_page(email: str = ""):
    return f"""<!doctype html><meta charset=utf-8><title>Opt out — getcontact</title>
<body style="font-family:system-ui;max-width:520px;margin:60px auto;padding:0 16px;color:#1b1f2a">
<h2>Remove my details</h2><p>Enter the email address you want removed. It will be deleted from the library and never emailed, revealed or exported again.</p>
<form onsubmit="event.preventDefault();fetch('/api/v1/optout',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email:this.email.value}})}}).then(r=>r.json()).then(j=>document.getElementById('o').textContent=j.suppressed?'Done. '+j.suppressed+' has been removed.':'Error')">
<input name=email value="{email}" placeholder="you@company.com" style="padding:8px;width:70%"> <button style="padding:8px 12px">Remove</button></form><p id=o></p></body>"""
