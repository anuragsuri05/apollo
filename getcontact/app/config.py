import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/getcontact.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
APP_NAME = os.getenv("APP_NAME", "getcontact")
USER_AGENT = os.getenv("USER_AGENT", "getcontact/0.1 (contact@example.com)")
SMTP_VERIFY = os.getenv("SMTP_VERIFY", "0") == "1"
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8000").rstrip("/")  # used in tracking pixels & opt-out links
MAIL_SYNC_MINUTES = int(os.getenv("MAIL_SYNC_MINUTES", "10"))
MAIL_SYNC_BATCH = int(os.getenv("MAIL_SYNC_BATCH", "500"))

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
COMPANIES_HOUSE_API_KEY = os.getenv("COMPANIES_HOUSE_API_KEY", "")
OPENCORPORATES_TOKEN = os.getenv("OPENCORPORATES_TOKEN", "")
DATA_GOV_IN_API_KEY = os.getenv("DATA_GOV_IN_API_KEY", "")

# Apollo-style plan table. Everything is free here; limits exist so the
# credit ledger and rate-limit headers behave like the real thing.
PLANS = {
    "free": {"credits_per_month": 1_000_000, "rate_per_minute": 600, "max_pages": 500, "per_page": 100},
}
CREDIT_COST = {"email": 1, "phone": 8, "export": 1, "enrich": 1}
PAGE_SIZE_MAX = 100
MAX_PAGES = 500
