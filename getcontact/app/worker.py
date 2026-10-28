"""Background worker: sends due sequence steps every 60 s and syncs connected mailboxes/CRMs every
MAIL_SYNC_MINUTES (contributions + bounce/reply feedback).  Run: python -m app.worker"""
import time
from datetime import datetime, timedelta

from .config import MAIL_SYNC_MINUTES
from .db import SessionLocal, init_db
from .mail_sync import sync_account
from .models import MailAccount
from .routers.sequences import process_due

if __name__ == "__main__":
    init_db()
    print("getcontact worker started")
    while True:
        db = SessionLocal()
        try:
            r = process_due(db)
            if any(r.values()):
                print("sequences", r, flush=True)
            cutoff = datetime.utcnow() - timedelta(minutes=MAIL_SYNC_MINUTES)
            due = db.query(MailAccount).filter((MailAccount.last_sync_at.is_(None)) | (MailAccount.last_sync_at <= cutoff)).all()
            for acct in due:
                if acct.contribute or acct.is_sender:
                    res = sync_account(db, acct)
                    print(f"sync {acct.kind}:{acct.label} →", res, flush=True)
        except Exception as e:  # noqa: BLE001
            print("worker error:", repr(e), flush=True)
        finally:
            db.close()
        time.sleep(60)
