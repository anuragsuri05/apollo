"""Mailbox + CRM sync: the two halves of the flywheel.

  contribute  — every address in From/To/Cc of real mail becomes a verified library record (with consent)
  is_sender   — the mailbox sequences send from is watched for bounces, replies and auto-replies, which
                flip emails to invalid / verified, stop sequences, and raise job-change signals
"""
import base64
import email as emaillib
import hashlib
import hmac
import imaplib
import mailbox
import re
from datetime import datetime
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

import httpx
from sqlalchemy.orm import Session

from .config import MAIL_SYNC_BATCH, SECRET_KEY
from .contrib import ContribStats, contribute_contact, extract_signature, parse_addresses
from .models import Contact, Contribution, EmailEvent, Enrollment, MailAccount, Person, Signal, User

BOUNCE_FROM_RX = re.compile(r"mailer-daemon|postmaster|mail delivery|delivery subsystem|bounce", re.I)
BOUNCE_SUBJ_RX = re.compile(r"undeliver|delivery (status|failure|has failed)|failure notice|returned mail|could not be delivered|not delivered|mail delivery failed|address not found", re.I)
AUTO_SUBJ_RX = re.compile(r"automatic reply|auto(-|\s)?reply|out of (the )?office|ooo|away from (my )?(email|office)|on leave|vacation", re.I)
LEFT_RX = re.compile(r"(no longer (with|at|works?|employed)|has left (the )?(company|organi[sz]ation|firm)|is no longer|moved on from|last day|"
                     r"left the (company|business|firm)|not (work|employed) (here|at)|retired from)", re.I)
NEW_CONTACT_RX = re.compile(r"(please (contact|reach out to|email)|contact|reach)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)[^@\n]{0,40}?([\w.+-]+@[\w-]+\.[\w.-]+)", re.I)
EMAIL_RX = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
FINAL_RCPT_RX = re.compile(r"(?:Final|Original)-Recipient:\s*rfc822;\s*([^\s;]+)", re.I)


# ---------- secret obfuscation (HMAC-SHA256 keystream; keeps credentials out of plain text in the DB) ----------
def _keystream(n: int, salt: bytes) -> bytes:
    out, i = b"", 0
    while len(out) < n:
        out += hmac.new(SECRET_KEY.encode(), salt + i.to_bytes(4, "big"), hashlib.sha256).digest()
        i += 1
    return out[:n]


def seal(secret: str) -> str:
    salt = hashlib.sha256(secret.encode()).digest()[:8]
    data = secret.encode()
    return base64.b64encode(salt + bytes(a ^ b for a, b in zip(data, _keystream(len(data), salt)))).decode()


def unseal(blob: str) -> str:
    raw = base64.b64decode(blob)
    salt, data = raw[:8], raw[8:]
    return bytes(a ^ b for a, b in zip(data, _keystream(len(data), salt))).decode()


# ---------- message handling ----------
def _hdr(msg, name) -> str:
    v = msg.get(name)
    if not v:
        return ""
    try:
        return str(make_header(decode_header(v)))
    except Exception:  # noqa: BLE001
        return str(v)


def _text_body(msg, limit=20000) -> str:
    parts = []
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type() == "text/plain" and not p.get_filename():
                try:
                    parts.append(p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", "replace"))
                except Exception:  # noqa: BLE001
                    pass
            if sum(len(x) for x in parts) > limit:
                break
    else:
        try:
            parts.append(msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", "replace"))
        except Exception:  # noqa: BLE001
            pass
    text = "\n".join(parts)
    if not text and msg.is_multipart():  # html-only mail: strip tags crudely
        for p in msg.walk():
            if p.get_content_type() == "text/html":
                try:
                    html = p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", "replace")
                    text = re.sub(r"<[^>]+>", "\n", re.sub(r"<(style|script).*?</\1>", "", html, flags=re.S | re.I))
                    text = re.sub(r"\n{2,}", "\n", text)
                except Exception:  # noqa: BLE001
                    pass
                break
    return text[:limit]


def _own_addresses(acct: MailAccount, user: User) -> set[str]:
    s = {user.email.lower()}
    if acct and acct.username and "@" in acct.username:
        s.add(acct.username.lower())
    return s


def process_message(db: Session, user: User, acct: MailAccount | None, msg, stats: ContribStats, source: str, contribute: bool, watch: bool):
    stats.messages += 1
    subj = _hdr(msg, "Subject")
    from_list = parse_addresses(_hdr(msg, "From"))
    sender = from_list[0][1] if from_list else ""
    try:
        seen = parsedate_to_datetime(msg.get("Date")).replace(tzinfo=None) if msg.get("Date") else None
    except Exception:  # noqa: BLE001
        seen = None
    own = _own_addresses(acct, user)
    body = None

    if watch:
        # ---- bounces ----
        is_bounce = bool(BOUNCE_FROM_RX.search(sender) or BOUNCE_SUBJ_RX.search(subj) or msg.get_content_type() == "multipart/report" or msg.get("X-Failed-Recipients"))
        if is_bounce:
            body = body or _text_body(msg)
            failed = set()
            if msg.get("X-Failed-Recipients"):
                failed.update(e.lower() for e in EMAIL_RX.findall(msg.get("X-Failed-Recipients")))
            failed.update(e.lower() for e in FINAL_RCPT_RX.findall(body))
            if not failed:
                cands = {e.lower() for e in EMAIL_RX.findall(body)} - own
                known = {c.email for c in db.query(Contact).filter(Contact.user_id == user.id, Contact.email.in_(list(cands))).all()} if cands else set()
                failed.update(known)
            for addr in failed:
                _mark_bounce(db, user, addr, subj)
            return
        # ---- auto replies / job change ----
        auto = bool(msg.get("Auto-Submitted") and msg.get("Auto-Submitted").lower() != "no") or bool(msg.get("X-Autoreply")) or bool(AUTO_SUBJ_RX.search(subj))
        if sender and sender not in own:
            contact = db.query(Contact).filter(Contact.user_id == user.id, Contact.email == sender).first()
            if contact:
                body = body or _text_body(msg)
                if auto:
                    left = LEFT_RX.search(body)
                    detail = (left.group(0) if left else "auto-reply")
                    db.add(Signal(user_id=user.id, person_id=contact.person_id, email=sender, kind="job_change" if left else "auto_reply", detail=detail[:300]))
                    if left:
                        _invalidate(db, sender, "job_change")
                        m = NEW_CONTACT_RX.search(body)
                        if m and contribute:
                            contribute_contact(db, user, m.group(3), m.group(4), seen_at=seen, source="auto_reply", stats=stats)
                else:
                    db.add(Signal(user_id=user.id, person_id=contact.person_id, email=sender, kind="reply", detail=subj[:200]))
                    for e in db.query(Enrollment).filter(Enrollment.contact_id == contact.id, Enrollment.status == "active").all():
                        e.status = "replied"
                        db.add(EmailEvent(enrollment_id=e.id, step_id=0, kind="replied", detail=subj[:200]))
                    for per in db.query(Person).filter(Person.email == sender).all():
                        per.email_status, per.last_verified_at = "verified", datetime.utcnow()
                    contact.email_status = "verified"
                    if contact.stage == "contacted":
                        contact.stage = "replied"

    if contribute:
        if BOUNCE_FROM_RX.search(sender) or (msg.get("Auto-Submitted") or "no").lower() != "no" or msg.get("List-Unsubscribe") or msg.get("Precedence", "").lower() in ("bulk", "list", "junk"):
            return  # newsletters / notifications are not people
        sig = {}
        if sender and sender not in own:
            body = body or _text_body(msg)
            sig = extract_signature(body)
        for name, addr in from_list:
            if addr not in own:
                contribute_contact(db, user, name, addr, title=sig.get("title"), phone=sig.get("phone"), seen_at=seen, source=source, stats=stats)
        for name, addr in parse_addresses(_hdr(msg, "To"), _hdr(msg, "Cc")):
            if addr not in own:
                contribute_contact(db, user, name, addr, seen_at=seen, source=source, stats=stats)


def _mark_bounce(db, user, addr, subj):
    _invalidate(db, addr, "bounce")
    db.add(Signal(user_id=user.id, email=addr, kind="bounce", detail=subj[:200]))
    for c in db.query(Contact).filter(Contact.user_id == user.id, Contact.email == addr).all():
        c.email_status = "invalid"
        for e in db.query(Enrollment).filter(Enrollment.contact_id == c.id, Enrollment.status == "active").all():
            e.status = "bounced"
            db.add(EmailEvent(enrollment_id=e.id, step_id=0, kind="bounced", detail=addr))


def _invalidate(db, addr, reason):
    for per in db.query(Person).filter(Person.email == addr).all():
        per.email_status = "invalid"
        per.last_verified_at = datetime.utcnow()


# ---------- IMAP ----------
def sync_imap(db: Session, user: User, acct: MailAccount, batch: int = MAIL_SYNC_BATCH) -> dict:
    stats = ContribStats()
    cls = imaplib.IMAP4_SSL if acct.use_ssl else imaplib.IMAP4
    try:
        M = cls(acct.host, acct.port, timeout=60)
        M.login(acct.username, unseal(acct.secret))
        M.select(acct.folder or "INBOX", readonly=True)
        typ, data = M.uid("search", None, f"UID {acct.last_uid + 1}:*")
        uids = [int(u) for u in (data[0].split() if data and data[0] else []) if int(u) > acct.last_uid]
        uids = uids[:batch]
        for uid in uids:
            typ, parts = M.uid("fetch", str(uid), "(BODY.PEEK[])")
            raw = next((p[1] for p in parts if isinstance(p, tuple)), None)
            if not raw:
                continue
            msg = emaillib.message_from_bytes(raw)
            process_message(db, user, acct, msg, stats, "imap", contribute=acct.contribute and user.contribute, watch=acct.is_sender)
            acct.last_uid = uid
            acct.messages_seen += 1
            if stats.messages % 50 == 0:
                db.commit()
        M.logout()
        acct.status, acct.error = "ok", None
    except Exception as e:  # noqa: BLE001
        acct.status, acct.error = "error", str(e)[:500]
    acct.last_sync_at = datetime.utcnow()
    db.add(Contribution(user_id=user.id, mail_account_id=acct.id, source="imap", **{k: v for k, v in stats.as_dict().items() if k != "skipped"}))
    db.commit()
    return {**stats.as_dict(), "status": acct.status, "error": acct.error}


# ---------- files: MBOX / EML (Google Takeout, Apple Mail, Thunderbird exports) ----------
def import_mbox(db: Session, user: User, path: str, watch: bool = False, limit: int = 0) -> dict:
    stats = ContribStats()
    for i, msg in enumerate(mailbox.mbox(path)):
        process_message(db, user, None, msg, stats, "mbox", contribute=user.contribute, watch=watch)
        if i % 200 == 0:
            db.commit()
        if limit and i + 1 >= limit:
            break
    db.add(Contribution(user_id=user.id, source="mbox", **{k: v for k, v in stats.as_dict().items() if k != "skipped"}))
    db.commit()
    return stats.as_dict()


def import_eml_bytes(db: Session, user: User, raw: bytes, watch: bool = False) -> dict:
    stats = ContribStats()
    process_message(db, user, None, emaillib.message_from_bytes(raw), stats, "eml", contribute=user.contribute, watch=watch)
    db.add(Contribution(user_id=user.id, source="eml", **{k: v for k, v in stats.as_dict().items() if k != "skipped"}))
    db.commit()
    return stats.as_dict()


# ---------- HubSpot (free CRM, private-app token) ----------
def sync_hubspot(db: Session, user: User, acct: MailAccount, batch: int = 2000) -> dict:
    stats = ContribStats()
    token = unseal(acct.secret)
    after, n = acct.cursor, 0
    try:
        with httpx.Client(timeout=30, headers={"Authorization": f"Bearer {token}"}) as c:
            while True:
                params = {"limit": 100, "properties": "firstname,lastname,email,jobtitle,phone,mobilephone,company,website,hs_linkedin_url"}
                if after:
                    params["after"] = after
                r = c.get("https://api.hubapi.com/crm/v3/objects/contacts", params=params)
                r.raise_for_status()
                j = r.json()
                for row in j.get("results", []):
                    p = row.get("properties") or {}
                    if p.get("email"):
                        contribute_contact(db, user, f"{p.get('firstname') or ''} {p.get('lastname') or ''}".strip(), p["email"], title=p.get("jobtitle"),
                                           phone=p.get("mobilephone") or p.get("phone"), source="hubspot", stats=stats, linkedin_url=p.get("hs_linkedin_url"),
                                           company_name=p.get("company"))
                    stats.messages += 1
                    n += 1
                after = ((j.get("paging") or {}).get("next") or {}).get("after")
                acct.cursor = after
                db.commit()
                if not after or n >= batch:
                    break
        acct.status, acct.error = "ok", None
    except Exception as e:  # noqa: BLE001
        acct.status, acct.error = "error", str(e)[:500]
    acct.last_sync_at = datetime.utcnow()
    acct.messages_seen += n
    db.add(Contribution(user_id=user.id, mail_account_id=acct.id, source="hubspot", **{k: v for k, v in stats.as_dict().items() if k != "skipped"}))
    db.commit()
    return {**stats.as_dict(), "status": acct.status, "error": acct.error}


def sync_account(db: Session, acct: MailAccount) -> dict:
    user = db.get(User, acct.user_id)
    return sync_hubspot(db, user, acct) if acct.kind == "hubspot" else sync_imap(db, user, acct)
