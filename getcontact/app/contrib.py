"""Contributor network: turn consented mailbox / CRM traffic into library records.

Rules (mirrors what Apollo/ZoomInfo/Lusha do, with the guard-rails they publish):
  * only business addresses — freemail (gmail, yahoo, …) and role accounts (info@, noreply@) are dropped
  * an address seen in real mail traffic is `verified`; later bounces flip it to `invalid`
  * suppressed (opted-out) addresses are never stored
  * every stored person keeps `contributors` (how many mailboxes saw them) and `last_seen_at`
"""
import re
from datetime import datetime
from email.utils import getaddresses

from sqlalchemy.orm import Session

from .email_engine import _FREEMAIL as FREEMAIL, learn_pattern, mx_valid
from .models import Organization, Person, Signal, Suppression, User
from .util import domain_from_url, infer_department, infer_seniority, norm_name, norm_person, split_name

ROLE_LOCALS = {"info", "noreply", "no-reply", "donotreply", "do-not-reply", "support", "sales", "admin", "hello", "contact", "team",
               "billing", "help", "news", "newsletter", "notifications", "notification", "mailer-daemon", "postmaster", "hr", "jobs",
               "careers", "marketing", "security", "abuse", "alerts", "alert", "updates", "service", "customerservice", "orders", "bounce",
               "bounces", "reply", "mail", "email", "office", "accounts", "invoice", "invoices", "press", "media", "webmaster", "root"}
ROLE_RX = re.compile(r"^(.*[-_.+])?(" + "|".join(re.escape(r) for r in ROLE_LOCALS) + r")([-_.+].*)?$")
NOTIFY_DOMAIN_RX = re.compile(r"(^|\.)(linkedin|facebook|facebookmail|twitter|x|github|slack|notion|atlassian|zoom|calendly|google|googlemail|"
                              r"apple|amazon|amazonses|sendgrid|mailchimp|mailgun|hubspot|salesforce|intercom|zendesk|stripe|paypal|docusign|"
                              r"dropbox|microsoft|office365|outlook|live|hotmail|yahoo|gmail|proton|protonmail|icloud|substack|medium|quora|"
                              r"indeed|glassdoor|uber|airbnb|booking|expedia)\.(com|net|io|co|org|me|in)$")

TITLE_WORDS = r"(chief|officer|ceo|cto|cfo|coo|cmo|cro|cio|ciso|president|vice|vp|svp|evp|avp|director|head|manager|lead|founder|co-founder|owner|partner|principal|" \
              r"engineer|developer|architect|analyst|consultant|specialist|associate|executive|account|sales|marketing|product|design|designer|" \
              r"recruiter|hr|talent|operations|finance|controller|counsel|attorney|advisor|adviser|scientist|researcher|professor|dean|editor|" \
              r"journalist|coordinator|administrator|assistant|intern|strategist|evangelist|advocate|representative|rep|agent|broker|realtor|" \
              r"md|managing|general|regional|global|country|senior|sr|junior|jr|staff|team)"
TITLE_RX = re.compile(r"^(?=.{3,80}$)(?!.*(http|www\.|@|\d{5,}))(.*\b" + TITLE_WORDS + r"\b.*)$", re.I)
PHONE_RX = re.compile(r"(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}(?:[\s.-]?\d{1,4})?")
PHONE_LABEL_RX = re.compile(r"\b(mob|mobile|cell|tel|phone|ph|direct|dd|m|t|p|c)\b\s*[:.]?", re.I)
SIG_START_RX = re.compile(r"^(--\s*$|__+$|best( regards)?|regards|kind regards|thanks( and regards)?|thank you|cheers|sincerely|warm regards|many thanks)[,.!]?\s*$", re.I)
QUOTE_RX = re.compile(r"^(>|On .+ wrote:|From: |-----Original Message-----|_{5,})", re.I)


def is_business_address(email: str) -> bool:
    if not email or "@" not in email:
        return False
    local, domain = email.lower().rsplit("@", 1)
    if domain in FREEMAIL or NOTIFY_DOMAIN_RX.search(domain):
        return False
    if ROLE_RX.match(local):
        return False
    if "." not in domain or len(local) > 64 or re.search(r"[^a-z0-9._+\-]", local):
        return False
    if re.search(r"\d{6,}", local) or local.count("+") > 0:  # ticket ids, plus-addressing
        return False
    return True


def parse_addresses(*header_values) -> list[tuple[str, str]]:
    out = []
    for name, addr in getaddresses([h for h in header_values if h]):
        addr = addr.strip().lower()
        if "@" in addr:
            out.append((name.strip().strip('"'), addr))
    return out


def name_from_parts(display: str, email: str) -> tuple[str, str]:
    """Return (first, last) from a display name, falling back to the local part (first.last → First Last)."""
    d = (display or "").strip()
    d = re.sub(r"\s*\(.*?\)\s*|\s*<.*?>\s*|\s*\|.*$|\s+via\s+.*$", "", d).strip()
    if "," in d and len(d.split(",")) == 2:
        last, first = [x.strip() for x in d.split(",")]
        d = f"{first} {last}"
    if d and not re.search(r"@|\d|noreply|no-reply|team$|support$", d, re.I) and len(d.split()) >= 2:
        first, last = split_name(d)
        return first.title() if first.islower() or first.isupper() else first, last.title() if last.islower() or last.isupper() else last
    local = email.split("@")[0]
    parts = [p for p in re.split(r"[._\-]", local) if p.isalpha()]
    if len(parts) >= 2 and len(parts[-1]) > 1:  # first.last, f.last, first_last …
        return parts[0].title(), parts[-1].title()
    return "", ""  # single-token names are too ambiguous to be worth storing


def extract_signature(text: str) -> dict:
    """Pull a job title and phone from the last lines of a plain-text body, before any quoted reply."""
    if not text:
        return {}
    lines = []
    for ln in text.replace("\r", "").split("\n"):
        if QUOTE_RX.match(ln.strip()):
            break
        lines.append(ln.rstrip())
    tail = [l.strip() for l in lines[-14:] if l.strip()]
    # start after a sign-off if present
    for i, l in enumerate(tail):
        if SIG_START_RX.match(l):
            tail = tail[i + 1:]
            break
    out = {}
    for l in tail:
        if "title" not in out and TITLE_RX.match(l) and not PHONE_RX.fullmatch(l.strip()):
            cand = re.split(r"\s[|•·]\s|,\s(?=[A-Z])", l)[0].strip(" -|,")
            if 2 < len(cand) <= 80:
                out["title"] = cand
        if "phone" not in out:
            m = PHONE_RX.search(PHONE_LABEL_RX.sub("", l))
            if m and sum(ch.isdigit() for ch in m.group(0)) >= 10 and not re.search(r"\b(19|20)\d{2}\b", m.group(0)):
                out["phone"] = m.group(0).strip()
    return out


class ContribStats:
    def __init__(self):
        self.messages = self.people_added = self.people_updated = self.orgs_added = self.skipped = 0

    def as_dict(self):
        return {k: v for k, v in vars(self).items()}


def contribute_contact(db: Session, user: User, display: str, email: str, title: str | None = None, phone: str | None = None,
                       seen_at: datetime | None = None, source: str = "contributor", stats: ContribStats | None = None,
                       linkedin_url: str | None = None, company_name: str | None = None) -> Person | None:
    email = (email or "").strip().lower()
    if not is_business_address(email) or db.get(Suppression, email):
        if stats:
            stats.skipped += 1
        return None
    first, last = name_from_parts(display, email)
    if not first:
        if stats:
            stats.skipped += 1
        return None
    domain = email.rsplit("@", 1)[1]
    org = db.query(Organization).filter(Organization.domain == domain).first()
    if not org:
        label = company_name or domain.split(".")[0].capitalize()
        org = Organization(name=label, name_norm=norm_name(label), domain=domain, website=f"https://{domain}", source="contributor",
                           source_id=domain, mx_valid=mx_valid(domain))
        db.add(org)
        db.flush()
        if stats:
            stats.orgs_added += 1
    elif company_name and org.source in ("tranco", "contributor") and org.name.lower() == domain.split(".")[0]:
        org.name, org.name_norm = company_name, norm_name(company_name)
    per = db.query(Person).filter(Person.email == email).first()
    created = False
    if not per:
        per = db.query(Person).filter(Person.organization_id == org.id, Person.name_norm == norm_person(f"{first} {last}")).first()
    if not per:
        per = Person(source=source, source_id=email, first_name=first, last_name=last, full_name=f"{first} {last}".strip(),
                     name_norm=norm_person(f"{first} {last}"), organization_id=org.id, organization_name=org.name, contributors=0)
        db.add(per)
        created = True
    if per.email != email or per.email_status != "verified":
        per.email, per.email_status = email, "verified"
        per.last_verified_at = datetime.utcnow()
    if title and (not per.title or per.source in ("tranco", "contributor") and len(title) > len(per.title or "")):
        per.title = title[:250]
        per.seniority, per.department = infer_seniority(title), infer_department(title)
    if phone and not per.phone:
        per.phone = phone[:60]
    if linkedin_url and not per.linkedin_url:
        per.linkedin_url = linkedin_url
    per.last_seen_at = max(seen_at or datetime.utcnow(), per.last_seen_at or datetime.min)
    per.contributors = (per.contributors or 0) + (1 if created else 0)
    learn_pattern(db, domain, first, last, email)
    if stats:
        if created:
            stats.people_added += 1
        else:
            stats.people_updated += 1
    if created:
        db.add(Signal(user_id=user.id, person_id=None, email=email, kind="new_contact", detail=f"{first} {last} @ {org.name} via {source}"))
    return per


def suppress(db: Session, email: str, reason: str = "optout"):
    email = email.strip().lower()
    if not db.get(Suppression, email):
        db.add(Suppression(email=email, reason=reason))
    for per in db.query(Person).filter(Person.email == email).all():
        per.email, per.email_status = None, "suppressed"
    from .models import Contact, Enrollment
    for c in db.query(Contact).filter(Contact.email == email).all():
        c.email, c.email_status = None, "suppressed"
        for e in db.query(Enrollment).filter(Enrollment.contact_id == c.id, Enrollment.status == "active").all():
            e.status = "paused"
    db.commit()
