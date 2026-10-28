"""Shared ingestion plumbing: HTTP client, upserts with cross-source dedup, run bookkeeping."""
import json
import sys
import time
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.config import USER_AGENT
from app.db import SessionLocal, init_db
from app.email_engine import learn_pattern
from app.models import IngestRun, Organization, Person
from app.util import domain_from_url, infer_department, infer_seniority, norm_name, norm_person, split_name

ENTITY_WORDS = (" llc", " l.l.c", " lp", " l.p", " trust", " fund", " inc", " corp", " capital", " partners", " holdings",
                " ltd", " limited", " plc", " management", " advisors", " associates", " foundation", " group", " co.", " company", " bank", " sa ", " gmbh")


def looks_like_entity(name: str) -> bool:
    n = f" {name.lower()} "
    return any(w in n for w in ENTITY_WORDS)


class Ingestor:
    def __init__(self, source: str, args, batch: int = 500):
        init_db()
        self.source = source
        self.db: Session = SessionLocal(autoflush=True)  # pending rows must be visible to dedup queries
        self.run = IngestRun(source=source, args=json.dumps({k: v for k, v in vars(args).items() if k != "func"}, default=str))
        self.db.add(self.run)
        self.db.commit()
        self.batch = batch
        self._pending = 0
        self._org_cache: dict[tuple, int] = {}
        self._domain_cache: dict[str, int] = {}
        self.http = httpx.Client(headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/csv, */*"},
                                 timeout=httpx.Timeout(60.0, connect=20.0), follow_redirects=True)
        self.t0 = time.time()

    # ---------- http ----------
    def get(self, url, retries=4, **kw):
        for i in range(retries):
            try:
                r = self.http.get(url, **kw)
                if r.status_code == 429 or r.status_code >= 500:
                    wait = int(r.headers.get("retry-after", 2 ** (i + 1)))
                    self.log(f"HTTP {r.status_code} on {url[:80]} — waiting {wait}s")
                    time.sleep(wait)
                    continue
                return r
            except (httpx.TransportError, httpx.TimeoutException) as e:
                self.log(f"net error {e!r} — retry {i + 1}")
                time.sleep(2 ** (i + 1))
        raise RuntimeError(f"giving up on {url}")

    def download(self, url, dest, **kw):
        with self.http.stream("GET", url, **kw) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            done = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    f.write(chunk)
                    done += len(chunk)
                    if total and done % (50 << 20) < (1 << 20):
                        self.log(f"  downloaded {done >> 20}MB / {total >> 20}MB")
        return dest

    # ---------- upserts ----------
    def upsert_org(self, name: str, source_id: str, **f) -> Organization | None:
        name = (name or "").strip()
        if not name:
            return None
        source = f.pop("source", self.source)
        domain = f.get("domain") or domain_from_url(f.get("website"))
        if domain:
            f["domain"] = domain
        key = (source, str(source_id))
        org = None
        oid = self._org_cache.get(key)
        if oid:
            org = self.db.get(Organization, oid)
        if org is None:
            org = self.db.query(Organization).filter(Organization.source == source, Organization.source_id == str(source_id)).first()
        if org is None and domain:
            oid = self._domain_cache.get(domain)
            org = self.db.get(Organization, oid) if oid else self.db.query(Organization).filter(Organization.domain == domain).first()
        if org is None:
            for k in ("lei", "cik"):
                if f.get(k):
                    org = self.db.query(Organization).filter(getattr(Organization, k) == str(f[k])).first()
                    if org:
                        break
        if org is None:
            org = Organization(name=name, name_norm=norm_name(name), source=source, source_id=str(source_id))
            self.db.add(org)
            self.run.orgs_upserted += 1
        else:
            if not org.name_norm:
                org.name_norm = norm_name(org.name)
        for k, v in f.items():
            if v in (None, "", []):
                continue
            if getattr(org, k, None) in (None, "") or k in ("employee_count", "revenue", "status", "updated_at"):
                setattr(org, k, v)
        self.db.flush()
        self._org_cache[key] = org.id
        if domain:
            self._domain_cache[domain] = org.id
        self._tick()
        return org

    def upsert_person(self, full_name: str, source_id: str, org: Organization | None = None, **f) -> Person | None:
        full_name = " ".join((full_name or "").split())
        if not full_name or looks_like_entity(full_name) and not f.get("force"):
            return None
        f.pop("force", None)
        source = f.pop("source", self.source)
        first, last = f.pop("first_name", None), f.pop("last_name", None)
        if not (first or last):
            first, last = split_name(full_name)
        nn = norm_person(full_name)
        per = self.db.query(Person).filter(Person.source == source, Person.source_id == str(source_id)).first()
        if per is None and org is not None:
            per = self.db.query(Person).filter(Person.organization_id == org.id, Person.name_norm == nn).first()
        if per is None:
            per = Person(source=source, source_id=str(source_id), full_name=full_name, name_norm=nn, first_name=first, last_name=last)
            self.db.add(per)
            self.run.people_upserted += 1
        if org is not None:
            per.organization_id = org.id
            per.organization_name = org.name
        title = f.get("title")
        if title and (not per.title or len(title) > len(per.title or "")):
            per.title = title[:250]
            per.seniority = infer_seniority(title)
            per.department = infer_department(title)
        for k in ("linkedin_url", "city", "state", "country", "phone", "source_url"):
            if f.get(k) and not getattr(per, k):
                setattr(per, k, f[k])
        email = f.get("email")
        if email:
            email = email.lower().strip()
            status = f.get("email_status", "verified")
            rank = {"verified": 3, "mx_valid": 2, "guessed": 1, "invalid": 0, "none": 0}
            if rank.get(status, 0) >= rank.get(per.email_status, 0):
                per.email, per.email_status = email, status
                if status == "verified" and org is not None and org.domain:
                    learn_pattern(self.db, org.domain, first, last, email)
        self._tick()
        return per

    # ---------- bookkeeping ----------
    def _tick(self):
        self._pending += 1
        self.run.rows_in += 1
        if self._pending >= self.batch:
            self.commit()

    def commit(self):
        self.db.commit()
        self._pending = 0

    def log(self, msg):
        el = int(time.time() - self.t0)
        print(f"[{self.source} +{el}s] {msg}", file=sys.stderr, flush=True)

    def progress(self):
        self.log(f"rows={self.run.rows_in} orgs+={self.run.orgs_upserted} people+={self.run.people_upserted}")

    def finish(self, error: str | None = None):
        self.run.status = "failed" if error else "done"
        self.run.error = error
        self.run.finished_at = datetime.utcnow()
        self.db.commit()
        self.progress()
        self.db.close()
        self.http.close()
