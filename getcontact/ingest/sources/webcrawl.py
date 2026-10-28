"""Public-web crawler: a company's own site is the most authoritative free source for who works there.

For each organization with a domain: fetch the homepage, follow up to --pages internal links that look like
team / about / leadership / contact pages, and extract
  * people (name + title pairs from headings/cards)      → Person(source=webcrawl)
  * published email addresses (mailto: and text)         → verified emails + learned domain pattern
  * phone numbers (tel:) and the LinkedIn company URL    → Organization
Honours robots.txt, 1 request/sec per domain, identifies itself with USER_AGENT.

    python -m ingest.run webcrawl --from-db 500           # orgs with a domain and no known people
    python -m ingest.run webcrawl --domains stripe.com,razorpay.com
"""
import re
import time
import urllib.robotparser
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from sqlalchemy import exists

from app.config import USER_AGENT
from app.contrib import TITLE_RX, is_business_address
from app.email_engine import learn_pattern
from app.models import Organization, Person
from app.util import norm_person

LINK_RX = re.compile(r"(team|about|leadership|people|management|staff|contact|our-team|who-we-are|founders|board|executives|company)", re.I)
NAME_RX = re.compile(r"^(?:Dr\.?\s|Mr\.?\s|Ms\.?\s|Mrs\.?\s)?[A-Z][a-zA-Z'’\-]+(?:\s[A-Z]\.?)?(?:\s[A-Z][a-zA-Z'’\-]+){1,2}$")
EMAIL_RX = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
STOP = {"privacy policy", "terms of service", "all rights reserved", "read more", "learn more", "contact us", "about us", "our team",
        "get started", "sign in", "log in", "united states", "new york", "san francisco", "case studies", "press releases"}


def add_args(p):
    p.add_argument("--domains", help="comma-separated list")
    p.add_argument("--from-db", type=int, default=0, help="pick N organizations with a domain and no people (largest first)")
    p.add_argument("--pages", type=int, default=6, help="max sub-pages per domain")
    p.add_argument("--delay", type=float, default=1.0)


def _soup(ing, url):
    try:
        r = ing.http.get(url, timeout=15, headers={"Accept": "text/html,*/*"})
        if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
            return None, r.url
        return BeautifulSoup(r.text[:1_500_000], "lxml"), str(r.url)
    except Exception:  # noqa: BLE001
        return None, url


def _allowed(domain, path="/"):
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.set_url(f"https://{domain}/robots.txt")
        rp.read()
        return rp.can_fetch(USER_AGENT.split("/")[0], f"https://{domain}{path}")
    except Exception:  # noqa: BLE001
        return True


def _people_from(soup):
    """Heuristic: a short name-like text node whose next text block looks like a job title."""
    found = {}
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "strong", "b", "p", "span", "div", "a", "figcaption", "dt"]):
        if len(tag.find_all()) > 3:
            continue
        txt = " ".join(tag.get_text(" ", strip=True).split())
        if not (4 < len(txt) < 40) or not NAME_RX.match(txt) or txt.lower() in STOP:
            continue
        title = None
        nxt = tag.find_next_sibling()
        hops = 0
        while nxt is not None and hops < 3 and title is None:
            t = " ".join(nxt.get_text(" ", strip=True).split())
            if t and t != txt and len(t) < 90 and TITLE_RX.match(t):
                title = t
            nxt = nxt.find_next_sibling()
            hops += 1
        if title is None and tag.parent is not None:
            for sib in tag.parent.find_all(["p", "span", "div", "small", "em", "dd", "h4", "h5", "h6"], limit=6):
                t = " ".join(sib.get_text(" ", strip=True).split())
                if t and t != txt and len(t) < 90 and TITLE_RX.match(t):
                    title = t
                    break
        if title:
            found.setdefault(txt, title)
    return found


def crawl_domain(ing, org: Organization, max_pages: int, delay: float) -> dict:
    domain = org.domain
    stats = {"pages": 0, "people": 0, "emails": 0}
    if not _allowed(domain):
        ing.log(f"{domain}: robots.txt disallows")
        return stats
    home, final = _soup(ing, f"https://{domain}/")
    if home is None:
        home, final = _soup(ing, f"http://{domain}/")
    if home is None:
        return stats
    stats["pages"] += 1
    pages = [(final, home)]
    seen = {final.rstrip("/")}
    links = []
    for a in home.find_all("a", href=True):
        href = urljoin(final, a["href"])
        u = urlparse(href)
        if u.netloc.replace("www.", "") != domain.replace("www.", "") or u.scheme not in ("http", "https"):
            continue
        key = href.split("#")[0].split("?")[0].rstrip("/")
        if key in seen or not (LINK_RX.search(u.path) or LINK_RX.search(a.get_text(" ", strip=True) or "")):
            continue
        seen.add(key)
        links.append(key)
    for href in links[:max_pages]:
        time.sleep(delay)
        s, f = _soup(ing, href)
        if s is not None:
            pages.append((f, s))
            stats["pages"] += 1
    people, emails, phones, linkedin = {}, set(), set(), None
    for url, s in pages:
        for a in s.find_all("a", href=True):
            h = a["href"]
            if h.lower().startswith("mailto:"):
                emails.add(h[7:].split("?")[0].strip().lower())
            elif h.lower().startswith("tel:"):
                phones.add(re.sub(r"[^\d+]", "", h[4:])[:20])
            elif "linkedin.com/company/" in h and not linkedin:
                linkedin = h.split("?")[0]
        emails.update(e.lower() for e in EMAIL_RX.findall(s.get_text(" ")) if not e.lower().endswith((".png", ".jpg", ".gif", ".svg")))
        for name, title in _people_from(s).items():
            people.setdefault(name, (title, url))
    if linkedin and not org.linkedin_url:
        org.linkedin_url = linkedin
    if phones and not org.phone:
        org.phone = sorted(phones, key=len, reverse=True)[0]
    emails = {e for e in emails if e.endswith("@" + domain) or e.endswith("." + domain)}
    # people
    for name, (title, url) in people.items():
        per = ing.upsert_person(name, f"{domain}:{norm_person(name)}", org, title=title, source_url=url)
        if per:
            stats["people"] += 1
    # emails published by the company itself count as verified
    for e in emails:
        if not is_business_address(e):
            continue
        local = e.split("@")[0]
        match = None
        for name in people:
            parts = [p.lower() for p in re.split(r"\s+", name) if p.isalpha()]
            if len(parts) >= 2 and (parts[0] in local and parts[-1] in local or local in (parts[0], parts[-1], parts[0][0] + parts[-1])):
                match = name
                break
        if match:
            ing.upsert_person(match, f"{domain}:{norm_person(match)}", org, email=e, email_status="verified", source_url=people[match][1])
            first, last = match.split()[0], match.split()[-1]
            learn_pattern(ing.db, domain, first, last, e)
            stats["emails"] += 1
        elif not org.description or "email:" not in org.description:
            org.description = ((org.description or "") + f" email: {e}").strip()
    return stats


def run(ing, args):
    orgs = []
    if args.domains:
        for d in [x.strip().lower() for x in args.domains.split(",") if x.strip()]:
            o = ing.db.query(Organization).filter(Organization.domain == d).first() or ing.upsert_org(d.split(".")[0].capitalize(), d, domain=d, website=f"https://{d}")
            orgs.append(o)
    if args.from_db:
        q = ing.db.query(Organization).filter(Organization.domain.isnot(None), Organization.mx_valid.isnot(False)).filter(
            ~exists().where(Person.organization_id == Organization.id)).order_by(Organization.employee_count.desc().nullslast(), Organization.id)
        orgs += q.limit(args.from_db).all()
    ing.log(f"crawling {len(orgs)} domains")
    for i, o in enumerate(orgs):
        st = crawl_domain(ing, o, args.pages, args.delay)
        ing.run.rows_in += 1
        ing.log(f"{o.domain}: {st}")
        ing.commit()
        if args.limit and i + 1 >= args.limit:
            break
        time.sleep(args.delay)
