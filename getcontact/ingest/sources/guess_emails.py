"""Offline pass: give every person whose organization has a domain a pattern-based email.
Status is 'guessed' (default pattern) or 'mx_valid' (learned pattern + MX ok). With SMTP_VERIFY=1 it also probes.

    python -m ingest.run guess_emails --limit 50000 --seniority c_suite,vp,director
"""
from app.email_engine import guess_email
from app.models import Organization, Person


def add_args(p):
    p.add_argument("--seniority", help="comma list filter")
    p.add_argument("--verify", action="store_true", help="SMTP probe each address (slow)")


def run(ing, args):
    q = ing.db.query(Person).join(Organization, Person.organization_id == Organization.id).filter(Person.email.is_(None), Organization.domain.isnot(None))
    if args.seniority:
        q = q.filter(Person.seniority.in_(args.seniority.split(",")))
    if args.limit:
        q = q.limit(args.limit)
    n = 0
    for per in q.yield_per(1000):
        email, status, _ = guess_email(ing.db, per.first_name, per.last_name, per.organization.domain, verify=args.verify)
        if email and status != "invalid":
            per.email, per.email_status = email, status
        n += 1
        ing.run.rows_in += 1
        if n % 1000 == 0:
            ing.commit()
            ing.progress()
    ing.commit()
