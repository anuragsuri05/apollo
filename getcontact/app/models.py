from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text, ForeignKey,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def now():
    return datetime.utcnow()


# ---------------- accounts ----------------
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(32), default="free")
    team_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    contribute: Mapped[bool] = mapped_column(Boolean, default=False)  # consent: share contacts with the library
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Session(Base):
    __tablename__ = "sessions"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    prefix: Mapped[str] = mapped_column(String(12))
    label: Mapped[str] = mapped_column(String(100), default="default")
    is_master: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CreditLedger(Base):
    __tablename__ = "credit_ledger"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(32))     # email | phone | export | enrich
    amount: Mapped[int] = mapped_column(Integer)
    ref: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class ApiUsage(Base):
    __tablename__ = "api_usage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    endpoint: Mapped[str] = mapped_column(String(120), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


# ---------------- data graph ----------------
class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    name_norm: Mapped[str] = mapped_column(String(300), index=True, default="")
    domain: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    sic_code: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    naics_code: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), index=True, nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    city: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(60), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lei: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    ticker: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cik: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    company_number: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)
    status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email_pattern: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mx_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source: Mapped[str] = mapped_column(String(40), index=True, default="manual")
    source_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_org_source"),)


class Person(Base):
    __tablename__ = "people"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(120), default="")
    last_name: Mapped[str] = mapped_column(String(120), default="")
    full_name: Mapped[str] = mapped_column(String(250), index=True)
    name_norm: Mapped[str] = mapped_column(String(250), index=True, default="")
    title: Mapped[str | None] = mapped_column(String(250), index=True, nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    department: Mapped[str | None] = mapped_column(String(60), index=True, nullable=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    email_status: Mapped[str] = mapped_column(String(20), default="none")  # verified|mx_valid|guessed|invalid|none
    phone: Mapped[str | None] = mapped_column(String(60), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), index=True, nullable=True)
    city: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(40), index=True, default="manual")
    source_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)      # last time seen in real mail traffic
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    contributors: Mapped[int] = mapped_column(Integer, default=0)                       # how many mailboxes have seen this contact
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    organization = relationship("Organization", lazy="joined")
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_person_source"),
        Index("ix_people_org_name", "organization_id", "name_norm"),
    )


class EmailPattern(Base):
    __tablename__ = "email_patterns"
    domain: Mapped[str] = mapped_column(String(255), primary_key=True)
    pattern: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    samples: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class IngestRun(Base):
    __tablename__ = "ingest_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(40), index=True)
    args: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rows_in: Mapped[int] = mapped_column(Integer, default=0)
    orgs_upserted: Mapped[int] = mapped_column(Integer, default=0)
    people_upserted: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------- user workspace ----------------
class Contact(Base):
    """A person saved into a user's workspace (Apollo 'Contacts')."""
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True, nullable=True)
    first_name: Mapped[str] = mapped_column(String(120), default="")
    last_name: Mapped[str] = mapped_column(String(120), default="")
    title: Mapped[str | None] = mapped_column(String(250), nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_status: Mapped[str] = mapped_column(String(20), default="none")
    phone: Mapped[str | None] = mapped_column(String(60), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stage: Mapped[str] = mapped_column(String(40), default="new")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("user_id", "person_id", name="uq_contact_user_person"),)


class List(Base):
    __tablename__ = "lists"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(16), default="people")  # people | companies
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ListItem(Base):
    __tablename__ = "list_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("lists.id"), index=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("list_id", "person_id", "organization_id", name="uq_list_item"),)


class Sequence(Base):
    __tablename__ = "sequences"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class SequenceStep(Base):
    __tablename__ = "sequence_steps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sequence_id: Mapped[int] = mapped_column(ForeignKey("sequences.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=1)
    kind: Mapped[str] = mapped_column(String(16), default="email")  # email | call | task | linkedin
    delay_days: Mapped[int] = mapped_column(Integer, default=0)
    subject: Mapped[str] = mapped_column(String(300), default="")
    body: Mapped[str] = mapped_column(Text, default="")


class Enrollment(Base):
    __tablename__ = "enrollments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sequence_id: Mapped[int] = mapped_column(ForeignKey("sequences.id"), index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), index=True)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    next_run_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|finished|paused|bounced|replied
    token: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)  # open-tracking token
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("sequence_id", "contact_id", name="uq_enroll"),)


class EmailEvent(Base):
    __tablename__ = "email_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id"), index=True)
    step_id: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))  # sent | failed | skipped | opened | replied | bounced | task
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


# ---------------- contributor network & feedback loop ----------------
class MailAccount(Base):
    """A mailbox or CRM a user connected. `contribute` shares its contacts with the library (consent);
    `is_sender` means sequences go out from it, so we watch it for bounces, replies and auto-replies."""
    __tablename__ = "mail_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="imap")  # imap | hubspot
    label: Mapped[str] = mapped_column(String(100), default="")
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    port: Mapped[int] = mapped_column(Integer, default=993)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secret: Mapped[str | None] = mapped_column(Text, nullable=True)  # obfuscated with SECRET_KEY
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    folder: Mapped[str] = mapped_column(String(100), default="INBOX")
    last_uid: Mapped[int] = mapped_column(Integer, default=0)
    cursor: Mapped[str | None] = mapped_column(String(255), nullable=True)  # paging cursor for API sources
    contribute: Mapped[bool] = mapped_column(Boolean, default=True)
    is_sender: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="new")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    messages_seen: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Contribution(Base):
    __tablename__ = "contributions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mail_account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(20))  # imap | mbox | eml | csv | hubspot | extension
    messages: Mapped[int] = mapped_column(Integer, default=0)
    people_added: Mapped[int] = mapped_column(Integer, default=0)
    people_updated: Mapped[int] = mapped_column(Integer, default=0)
    orgs_added: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Suppression(Base):
    """Opt-outs. Suppressed addresses are never revealed, exported or emailed again."""
    __tablename__ = "suppressions"
    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    reason: Mapped[str] = mapped_column(String(100), default="optout")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    person_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # bounce | reply | auto_reply | job_change | open | new_contact
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
