import re
import unicodedata

SUFFIXES = r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|llc|plc|gmbh|ag|sa|s\.a|bv|nv|pvt|private|pty|llp|lp|holdings?|group|the)\b"

SENIORITY_RULES = [
    ("owner", r"\bowner\b|\bproprietor\b"),
    ("founder", r"\bfounder\b|\bco-?founder\b"),
    ("c_suite", r"\bchief\b|\bc[a-z]o\b|\bpresident\b|\bchair(man|woman|person)?\b|\bmanaging director\b|\bmd\b"),
    ("partner", r"\bpartner\b"),
    ("vp", r"\bvice president\b|\bvp\b|\bsvp\b|\bevp\b|\bavp\b"),
    ("head", r"\bhead\b"),
    ("director", r"\bdirector\b"),
    ("manager", r"\bmanager\b|\blead\b|\bsupervisor\b"),
    ("senior", r"\bsenior\b|\bsr\.?\b|\bprincipal\b|\bstaff\b"),
    ("intern", r"\bintern\b|\btrainee\b"),
]
DEPARTMENT_RULES = [
    ("engineering", r"engineer|developer|software|devops|sre|architect|cto|technology|technical"),
    ("sales", r"\bsales\b|account executive|business development|\bbdr\b|\bsdr\b|revenue|cro\b"),
    ("marketing", r"marketing|growth|brand|content|seo|cmo\b|communications"),
    ("finance", r"finance|financial|accounting|controller|treasur|cfo\b|audit|tax"),
    ("operations", r"operations|operating|coo\b|supply chain|logistics|procurement"),
    ("hr", r"human resources|\bhr\b|people|talent|recruit|chro\b"),
    ("legal", r"legal|counsel|compliance|secretary"),
    ("product", r"product|design|ux|cpo\b"),
    ("executive", r"chief executive|ceo\b|president|founder|owner|chair|managing director|director"),
    ("it", r"information|\bit\b|security|ciso|cio\b|data"),
]


def norm_name(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(SUFFIXES, " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_person(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def split_name(full: str):
    parts = [p for p in re.split(r"\s+", (full or "").strip()) if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


def sec_name_to_first_last(name: str):
    """SEC insider names are 'LAST FIRST MIDDLE' (sometimes 'LAST, FIRST')."""
    if not name:
        return "", "", ""
    n = name.replace(",", " ").strip()
    parts = [p for p in n.split() if p]
    if len(parts) == 1:
        return parts[0].title(), "", parts[0].title()
    last, first = parts[0], parts[1]
    first, last = first.title(), last.title()
    return first, last, f"{first} {last}"


def infer_seniority(title: str | None):
    t = (title or "").lower()
    for label, rx in SENIORITY_RULES:
        if re.search(rx, t):
            return label
    return "entry" if t else None


def infer_department(title: str | None):
    t = (title or "").lower()
    for label, rx in DEPARTMENT_RULES:
        if re.search(rx, t):
            return label
    return None


def domain_from_url(url: str | None):
    if not url:
        return None
    u = url.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.split("/")[0].split("?")[0].split(":")[0]
    if "." not in u or " " in u:
        return None
    return u


EMPLOYEE_RANGES = [(1, 10), (11, 20), (21, 50), (51, 100), (101, 200), (201, 500), (501, 1000), (1001, 2000), (2001, 5000), (5001, 10000), (10001, 10**9)]


def employee_range(n: int | None):
    if n is None:
        return None
    for lo, hi in EMPLOYEE_RANGES:
        if lo <= n <= hi:
            return f"{lo},{hi if hi < 10**9 else ''}"
    return None
