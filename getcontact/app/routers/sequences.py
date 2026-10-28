"""Email sequences (Apollo 'Engage') with open tracking, bounce/reply feedback and opt-out links."""
import html as htmllib
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import make_msgid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import current_user
from ..config import PUBLIC_URL, SMTP_FROM, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER
from ..db import get_db
from ..models import Contact, EmailEvent, Enrollment, Sequence, SequenceStep, Suppression, User, Signal

router = APIRouter(prefix="/api/v1", tags=["sequences"])
GIF = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"


class SeqIn(BaseModel):
    name: str


class StepIn(BaseModel):
    kind: str = "email"
    delay_days: int = 0
    subject: str = ""
    body: str = ""


class EnrollIn(BaseModel):
    contact_ids: list[int]


def _render(tpl: str, c: Contact) -> str:
    vals = {"first_name": c.first_name, "last_name": c.last_name, "name": f"{c.first_name} {c.last_name}".strip(),
            "title": c.title or "", "company": c.organization_name or "", "email": c.email or ""}
    out = tpl
    for k, v in vals.items():
        out = out.replace("{{" + k + "}}", v).replace("{{ " + k + " }}", v)
    return out


def _send(to: str, subject: str, body: str, token: str | None, step_id: int) -> tuple[bool, str, str | None]:
    if not SMTP_HOST:
        return False, "SMTP not configured (dry run) — set SMTP_HOST/SMTP_USER/SMTP_PASS/SMTP_FROM in .env", None
    msg = EmailMessage()
    mid = make_msgid(domain=(SMTP_FROM or SMTP_USER).split("@")[-1])
    msg["From"], msg["To"], msg["Subject"], msg["Message-ID"] = SMTP_FROM or SMTP_USER, to, subject, mid
    optout = f"{PUBLIC_URL}/api/v1/optout?email={to}"
    msg["List-Unsubscribe"] = f"<{optout}>"
    msg.set_content(body + f"\n\n--\nTo stop receiving emails: {optout}")
    pixel = f'<img src="{PUBLIC_URL}/api/v1/t/{token}/{step_id}.gif" width="1" height="1" alt="">' if token else ""
    html = "<html><body style='font-family:sans-serif;font-size:14px'>" + htmllib.escape(body).replace("\n", "<br>") + \
           f"<br><br><span style='color:#888;font-size:11px'>--<br>To stop receiving emails: <a href='{optout}'>unsubscribe</a></span>{pixel}</body></html>"
    msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.starttls()
            if SMTP_USER:
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return True, "sent", mid
    except Exception as e:  # noqa: BLE001
        return False, str(e), None


def process_due(db: Session, sequence_id: int | None = None, now: datetime | None = None) -> dict:
    now = now or datetime.utcnow()
    q = db.query(Enrollment).filter(Enrollment.status == "active", Enrollment.next_run_at <= now)
    if sequence_id:
        q = q.filter(Enrollment.sequence_id == sequence_id)
    sent = failed = finished = skipped = 0
    for e in q.all():
        steps = db.query(SequenceStep).filter(SequenceStep.sequence_id == e.sequence_id).order_by(SequenceStep.position).all()
        if e.current_step >= len(steps):
            e.status = "finished"
            finished += 1
            continue
        step = steps[e.current_step]
        c = db.get(Contact, e.contact_id)
        if step.kind == "email":
            if not c or not c.email or c.email_status in ("invalid", "suppressed") or db.get(Suppression, c.email):
                db.add(EmailEvent(enrollment_id=e.id, step_id=step.id, kind="skipped", detail="no usable email (missing, bounced or opted out)"))
                e.status = "paused"
                skipped += 1
                continue
            ok, detail, mid = _send(c.email, _render(step.subject, c), _render(step.body, c), e.token, step.id)
            db.add(EmailEvent(enrollment_id=e.id, step_id=step.id, kind="sent" if ok else "failed", detail=detail, message_id=mid))
            sent += ok
            failed += (not ok)
            if ok and c.stage == "new":
                c.stage = "contacted"
        else:
            db.add(EmailEvent(enrollment_id=e.id, step_id=step.id, kind="task", detail=f"{step.kind}: {step.subject}"))
        e.current_step += 1
        if e.current_step >= len(steps):
            e.status = "finished"
            finished += 1
        else:
            e.next_run_at = now + timedelta(days=steps[e.current_step].delay_days)
    db.commit()
    return {"sent": sent, "failed": failed, "finished": finished, "skipped": skipped}


def _own(db, user, sid) -> Sequence:
    s = db.get(Sequence, sid)
    if not s or s.user_id != user.id:
        raise HTTPException(404)
    return s


def seq_dict(db: Session, s: Sequence):
    steps = db.query(SequenceStep).filter(SequenceStep.sequence_id == s.id).order_by(SequenceStep.position).all()
    enr = db.query(Enrollment).filter(Enrollment.sequence_id == s.id).all()
    ev = db.query(EmailEvent).join(Enrollment, EmailEvent.enrollment_id == Enrollment.id).filter(Enrollment.sequence_id == s.id).all()
    k = lambda kind: sum(x.kind == kind for x in ev)  # noqa: E731
    opened = len({x.enrollment_id for x in ev if x.kind == "opened"})
    return {"id": s.id, "name": s.name, "status": s.status, "created_at": s.created_at,
            "steps": [{"id": t.id, "position": t.position, "kind": t.kind, "delay_days": t.delay_days, "subject": t.subject, "body": t.body} for t in steps],
            "stats": {"enrolled": len(enr), "active": sum(e.status == "active" for e in enr), "finished": sum(e.status == "finished" for e in enr),
                      "sent": k("sent"), "failed": k("failed"), "skipped": k("skipped"), "opened": opened,
                      "replied": sum(e.status == "replied" for e in enr), "bounced": sum(e.status == "bounced" for e in enr)}}


@router.get("/sequences")
def list_seqs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"sequences": [seq_dict(db, s) for s in db.query(Sequence).filter(Sequence.user_id == user.id).all()]}


@router.post("/sequences")
def create_seq(s: SeqIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = Sequence(user_id=user.id, name=s.name)
    db.add(row)
    db.commit()
    return {"sequence": seq_dict(db, row)}


@router.get("/sequences/{sid}")
def get_seq(sid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"sequence": seq_dict(db, _own(db, user, sid))}


@router.delete("/sequences/{sid}")
def del_seq(sid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = _own(db, user, sid)
    db.query(SequenceStep).filter(SequenceStep.sequence_id == sid).delete()
    db.query(Enrollment).filter(Enrollment.sequence_id == sid).delete()
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.post("/sequences/{sid}/steps")
def add_step(sid: int, st: StepIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = _own(db, user, sid)
    pos = db.query(SequenceStep).filter(SequenceStep.sequence_id == sid).count() + 1
    db.add(SequenceStep(sequence_id=s.id, position=pos, kind=st.kind, delay_days=st.delay_days, subject=st.subject, body=st.body))
    db.commit()
    return {"sequence": seq_dict(db, s)}


@router.delete("/sequences/{sid}/steps/{step_id}")
def del_step(sid: int, step_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = _own(db, user, sid)
    st = db.get(SequenceStep, step_id)
    if st and st.sequence_id == sid:
        db.delete(st)
        db.commit()
    return {"sequence": seq_dict(db, s)}


@router.post("/sequences/{sid}/enroll")
def enroll(sid: int, e: EnrollIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = _own(db, user, sid)
    first = db.query(SequenceStep).filter(SequenceStep.sequence_id == sid).order_by(SequenceStep.position).first()
    delay = first.delay_days if first else 0
    n = 0
    for cid in e.contact_ids:
        c = db.get(Contact, cid)
        if not c or c.user_id != user.id:
            continue
        if db.query(Enrollment).filter(Enrollment.sequence_id == sid, Enrollment.contact_id == cid).first():
            continue
        db.add(Enrollment(sequence_id=sid, contact_id=cid, next_run_at=datetime.utcnow() + timedelta(days=delay), token=secrets.token_urlsafe(12)))
        n += 1
    db.commit()
    return {"enrolled": n, "sequence": seq_dict(db, s)}


@router.post("/sequences/{sid}/run")
def run_now(sid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _own(db, user, sid)
    return process_due(db, sid)


@router.get("/sequences/{sid}/events")
def events(sid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _own(db, user, sid)
    rows = db.query(EmailEvent, Enrollment).join(Enrollment, EmailEvent.enrollment_id == Enrollment.id).filter(Enrollment.sequence_id == sid).order_by(EmailEvent.id.desc()).limit(200).all()
    return {"events": [{"id": ev.id, "contact_id": en.contact_id, "step_id": ev.step_id, "kind": ev.kind, "detail": ev.detail, "at": ev.created_at} for ev, en in rows]}


# ---------- open tracking pixel (public) ----------
@router.get("/t/{token}/{step_id}.gif", include_in_schema=False)
def pixel(token: str, step_id: int, db: Session = Depends(get_db)):
    e = db.query(Enrollment).filter(Enrollment.token == token).first()
    if e:
        already = db.query(EmailEvent).filter(EmailEvent.enrollment_id == e.id, EmailEvent.step_id == step_id, EmailEvent.kind == "opened").first()
        if not already:
            db.add(EmailEvent(enrollment_id=e.id, step_id=step_id, kind="opened", detail="pixel"))
            c = db.get(Contact, e.contact_id)
            seq = db.get(Sequence, e.sequence_id)
            db.add(Signal(user_id=seq.user_id if seq else None, person_id=c.person_id if c else None, email=c.email if c else None, kind="open", detail=f"sequence {e.sequence_id} step {step_id}"))
            db.commit()
    return Response(content=GIF, media_type="image/gif", headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})
