"""Email pattern inference + verification.

Pattern names follow Hunter/Apollo conventions:
  {first}.{last}  {first}{last}  {f}{last}  {first}_{last}  {first}  {last}
  {f}.{last}  {first}{l}  {last}.{first}  {last}{first}  {first}-{last}
"""
import re
import smtplib
import socket
import time
import unicodedata

from sqlalchemy.orm import Session

from .config import SMTP_VERIFY
from .models import EmailPattern, Organization

PATTERNS = {
    "{first}.{last}": lambda f, l: f"{f}.{l}",
    "{first}{last}": lambda f, l: f"{f}{l}",
    "{f}{last}": lambda f, l: f"{f[:1]}{l}",
    "{first}_{last}": lambda f, l: f"{f}_{l}",
    "{first}": lambda f, l: f,
    "{last}": lambda f, l: l,
    "{f}.{last}": lambda f, l: f"{f[:1]}.{l}",
    "{first}{l}": lambda f, l: f"{f}{l[:1]}",
    "{last}.{first}": lambda f, l: f"{l}.{f}",
    "{last}{first}": lambda f, l: f"{l}{f}",
    "{first}-{last}": lambda f, l: f"{f}-{l}",
    "{f}-{last}": lambda f, l: f"{f[:1]}-{l}",
    "{last}{f}": lambda f, l: f"{l}{f[:1]}",
}
DEFAULT_PATTERN = "{first}.{last}"
_mx_cache: dict[str, tuple[bool, float]] = {}
_FREEMAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com", "proton.me", "protonmail.com", "rediffmail.com"}


def _clean(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", s)


def render(pattern: str, first: str, last: str, domain: str) -> str | None:
    f, l = _clean(first), _clean(last)
    if not f and not l:
        return None
    fn = PATTERNS.get(pattern)
    if not fn:
        return None
    local = fn(f or l, l or f)
    return f"{local}@{domain}" if local else None


def detect_pattern(first: str, last: str, email: str) -> str | None:
    try:
        local, domain = email.lower().split("@", 1)
    except ValueError:
        return None
    for name in PATTERNS:
        cand = render(name, first, last, domain)
        if cand and cand.split("@")[0] == local:
            return name
    return None


def mx_valid(domain: str, ttl: int = 86400) -> bool:
    domain = (domain or "").lower()
    if not domain:
        return False
    hit = _mx_cache.get(domain)
    if hit and time.time() - hit[1] < ttl:
        return hit[0]
    ok = False
    try:
        import dns.resolver
        res = dns.resolver.Resolver()
        res.lifetime = 4
        try:
            ok = len(res.resolve(domain, "MX")) > 0
        except Exception:
            ok = len(res.resolve(domain, "A")) > 0
    except Exception:
        try:
            socket.gethostbyname(domain)
            ok = True
        except Exception:
            ok = False
    _mx_cache[domain] = (ok, time.time())
    return ok


def smtp_probe(email: str, timeout: int = 8) -> bool | None:
    """RCPT-TO probe. Returns True/False or None when inconclusive (catch-all, blocked)."""
    try:
        import dns.resolver
        domain = email.split("@", 1)[1]
        mx = sorted((r.preference, str(r.exchange).rstrip(".")) for r in dns.resolver.resolve(domain, "MX"))
        host = mx[0][1]
        with smtplib.SMTP(host, 25, timeout=timeout) as s:
            s.helo("verify.getcontact.local")
            s.mail("probe@getcontact.local")
            code, _ = s.rcpt(email)
            if code in (250, 251):
                # catch-all check
                code2, _ = s.rcpt(f"zz-no-such-user-{int(time.time())}@{domain}")
                return None if code2 in (250, 251) else True
            if code in (550, 551, 553):
                return False
            return None
    except Exception:
        return None


def pattern_for_domain(db: Session, domain: str) -> tuple[str, float]:
    row = db.get(EmailPattern, domain)
    if row:
        return row.pattern, row.confidence
    return DEFAULT_PATTERN, 0.3


def learn_pattern(db: Session, domain: str, first: str, last: str, email: str):
    if not domain or domain in _FREEMAIL:
        return
    pat = detect_pattern(first, last, email)
    if not pat:
        return
    row = db.get(EmailPattern, domain)
    if row:
        if row.pattern == pat:
            row.samples += 1
            row.confidence = min(0.99, 0.5 + 0.1 * row.samples)
        elif row.samples <= 1:
            row.pattern, row.samples, row.confidence = pat, 1, 0.5
    else:
        db.add(EmailPattern(domain=domain, pattern=pat, confidence=0.6, samples=1))
    org = db.query(Organization).filter(Organization.domain == domain).first()
    if org:
        org.email_pattern = pat


def guess_email(db: Session, first: str, last: str, domain: str, verify: bool | None = None) -> tuple[str | None, str, float]:
    """Returns (email, status, confidence). status in verified|mx_valid|guessed|invalid|none."""
    if not domain or domain in _FREEMAIL or not (first or last):
        return None, "none", 0.0
    pat, conf = pattern_for_domain(db, domain)
    email = render(pat, first, last, domain)
    if not email:
        return None, "none", 0.0
    if not mx_valid(domain):
        return email, "invalid", 0.0
    status = "mx_valid" if conf >= 0.5 else "guessed"
    do_verify = SMTP_VERIFY if verify is None else verify
    if do_verify:
        r = smtp_probe(email)
        if r is True:
            return email, "verified", max(conf, 0.9)
        if r is False:
            # try the other common patterns before giving up
            for alt in ("{first}{last}", "{f}{last}", "{first}", "{first}_{last}"):
                if alt == pat:
                    continue
                e2 = render(alt, first, last, domain)
                if e2 and smtp_probe(e2) is True:
                    learn_pattern(db, domain, first, last, e2)
                    return e2, "verified", 0.9
            return email, "invalid", 0.0
    return email, status, conf
