"""Offline pass: resolve MX for organization domains (parallel), storing Organization.mx_valid."""
from concurrent.futures import ThreadPoolExecutor

from app.email_engine import mx_valid
from app.models import Organization


def add_args(p):
    p.add_argument("--workers", type=int, default=32)


def run(ing, args):
    q = ing.db.query(Organization).filter(Organization.domain.isnot(None), Organization.mx_valid.is_(None))
    if args.limit:
        q = q.limit(args.limit)
    rows = q.all()
    ing.log(f"checking {len(rows)} domains")
    with ThreadPoolExecutor(args.workers) as ex:
        for i, (o, ok) in enumerate(zip(rows, ex.map(lambda o: mx_valid(o.domain), rows))):
            o.mx_valid = ok
            ing.run.rows_in += 1
            if i % 2000 == 0:
                ing.commit()
                ing.progress()
    ing.commit()
