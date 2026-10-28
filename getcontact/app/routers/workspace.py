"""Contacts, lists, CSV export (Apollo 'Manage Records')."""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import current_user
from ..credits import charge
from ..db import get_db
from ..email_engine import guess_email
from ..models import Contact, List as ListModel, ListItem, Organization, Person, User
from ..search import collect_params, people_query, person_dict, org_dict

router = APIRouter(prefix="/api/v1", tags=["workspace"])


# ---------------- contacts ----------------
class ContactIn(BaseModel):
    person_id: int | None = None
    first_name: str = ""
    last_name: str = ""
    title: str | None = None
    organization_name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    stage: str | None = None
    notes: str | None = None


def contact_dict(c: Contact):
    return {"id": c.id, "person_id": c.person_id, "first_name": c.first_name, "last_name": c.last_name,
            "name": f"{c.first_name} {c.last_name}".strip(), "title": c.title, "organization_name": c.organization_name,
            "email": c.email, "email_status": c.email_status, "phone": c.phone, "linkedin_url": c.linkedin_url,
            "stage": c.stage, "notes": c.notes, "created_at": c.created_at}


@router.get("/contacts")
def list_contacts(page: int = 1, per_page: int = 50, q: str = "", user: User = Depends(current_user), db: Session = Depends(get_db)):
    qry = db.query(Contact).filter(Contact.user_id == user.id)
    if q:
        qry = qry.filter((Contact.first_name.ilike(f"%{q}%")) | (Contact.last_name.ilike(f"%{q}%")) | (Contact.organization_name.ilike(f"%{q}%")) | (Contact.email.ilike(f"%{q}%")))
    total = qry.count()
    rows = qry.order_by(Contact.created_at.desc()).offset((page - 1) * per_page).limit(min(per_page, 100)).all()
    return {"contacts": [contact_dict(c) for c in rows], "pagination": {"page": page, "per_page": per_page, "total_entries": total}}


@router.post("/contacts")
def create_contact(c: ContactIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if c.person_id:
        per = db.get(Person, c.person_id)
        if not per:
            raise HTTPException(404, {"error": "person_not_found"})
        row = db.query(Contact).filter(Contact.user_id == user.id, Contact.person_id == per.id).first()
        if row:
            return {"contact": contact_dict(row), "created": False}
        org = per.organization
        row = Contact(user_id=user.id, person_id=per.id, first_name=per.first_name, last_name=per.last_name, title=per.title,
                      organization_name=org.name if org else per.organization_name, linkedin_url=per.linkedin_url,
                      email=per.email, email_status=per.email_status, phone=None)
    else:
        row = Contact(user_id=user.id, first_name=c.first_name, last_name=c.last_name, title=c.title, organization_name=c.organization_name,
                      email=c.email, email_status="verified" if c.email else "none", phone=c.phone, linkedin_url=c.linkedin_url)
    row.stage = c.stage or "new"
    row.notes = c.notes
    db.add(row)
    db.commit()
    return {"contact": contact_dict(row), "created": True}


@router.patch("/contacts/{cid}")
def update_contact(cid: int, c: ContactIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(Contact, cid)
    if not row or row.user_id != user.id:
        raise HTTPException(404)
    for k, v in c.model_dump(exclude_none=True).items():
        if k != "person_id":
            setattr(row, k, v)
    db.commit()
    return {"contact": contact_dict(row)}


@router.delete("/contacts/{cid}")
def delete_contact(cid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(Contact, cid)
    if not row or row.user_id != user.id:
        raise HTTPException(404)
    db.delete(row)
    db.commit()
    return {"ok": True}


# ---------------- lists ----------------
class ListIn(BaseModel):
    name: str
    kind: str = "people"


class ListItemsIn(BaseModel):
    person_ids: list[int] = []
    organization_ids: list[int] = []


@router.get("/lists")
def lists(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(ListModel).filter(ListModel.user_id == user.id).all()
    out = []
    for l in rows:
        n = db.query(ListItem).filter(ListItem.list_id == l.id).count()
        out.append({"id": l.id, "name": l.name, "kind": l.kind, "count": n, "created_at": l.created_at})
    return {"lists": out}


@router.post("/lists")
def create_list(l: ListIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = ListModel(user_id=user.id, name=l.name, kind=l.kind)
    db.add(row)
    db.commit()
    return {"list": {"id": row.id, "name": row.name, "kind": row.kind}}


@router.delete("/lists/{lid}")
def delete_list(lid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    l = db.get(ListModel, lid)
    if not l or l.user_id != user.id:
        raise HTTPException(404)
    db.query(ListItem).filter(ListItem.list_id == lid).delete()
    db.delete(l)
    db.commit()
    return {"ok": True}


@router.post("/lists/{lid}/items")
def add_items(lid: int, items: ListItemsIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    l = db.get(ListModel, lid)
    if not l or l.user_id != user.id:
        raise HTTPException(404)
    added = 0
    for pid in items.person_ids:
        if not db.query(ListItem).filter(ListItem.list_id == lid, ListItem.person_id == pid).first():
            db.add(ListItem(list_id=lid, person_id=pid))
            added += 1
    for oid in items.organization_ids:
        if not db.query(ListItem).filter(ListItem.list_id == lid, ListItem.organization_id == oid).first():
            db.add(ListItem(list_id=lid, organization_id=oid))
            added += 1
    db.commit()
    return {"added": added}


@router.get("/lists/{lid}/items")
def list_items(lid: int, page: int = 1, per_page: int = 50, user: User = Depends(current_user), db: Session = Depends(get_db)):
    l = db.get(ListModel, lid)
    if not l or l.user_id != user.id:
        raise HTTPException(404)
    q = db.query(ListItem).filter(ListItem.list_id == lid)
    total = q.count()
    rows = q.offset((page - 1) * per_page).limit(min(per_page, 100)).all()
    people = [person_dict(db.get(Person, r.person_id)) for r in rows if r.person_id]
    orgs = [org_dict(db.get(Organization, r.organization_id)) for r in rows if r.organization_id]
    return {"list": {"id": l.id, "name": l.name, "kind": l.kind}, "people": people, "organizations": orgs,
            "pagination": {"page": page, "per_page": per_page, "total_entries": total}}


# ---------------- export ----------------
PERSON_COLS = ["id", "first_name", "last_name", "title", "seniority", "department", "email", "email_status", "phone",
               "linkedin_url", "city", "state", "country", "organization_name", "organization_domain", "organization_industry",
               "organization_employees", "organization_country", "source", "source_url"]


def _person_row(p: Person, db: Session, reveal: bool):
    o = p.organization
    email, status = p.email, p.email_status
    if reveal and not email and o and o.domain:
        email, status, _ = guess_email(db, p.first_name, p.last_name, o.domain)
    return [p.id, p.first_name, p.last_name, p.title, p.seniority, p.department, email if reveal else "", status if reveal else "",
            p.phone if reveal else "", p.linkedin_url, p.city, p.state, p.country, o.name if o else p.organization_name,
            o.domain if o else "", o.industry if o else "", o.employee_count if o else "", o.country if o else "", p.source, p.source_url]


def _csv_stream(header, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    yield buf.getvalue()
    for r in rows:
        buf.seek(0)
        buf.truncate()
        w.writerow(r)
        yield buf.getvalue()


@router.get("/contacts/export.csv")
def export_contacts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Contact).filter(Contact.user_id == user.id).all()
    header = ["id", "first_name", "last_name", "title", "organization_name", "email", "email_status", "phone", "linkedin_url", "stage", "notes"]
    data = [[c.id, c.first_name, c.last_name, c.title, c.organization_name, c.email, c.email_status, c.phone, c.linkedin_url, c.stage, c.notes] for c in rows]
    return StreamingResponse(_csv_stream(header, data), media_type="text/csv", headers={"content-disposition": "attachment; filename=contacts.csv"})


@router.get("/lists/{lid}/export.csv")
def export_list(lid: int, reveal: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
    l = db.get(ListModel, lid)
    if not l or l.user_id != user.id:
        raise HTTPException(404)
    items = db.query(ListItem).filter(ListItem.list_id == lid).all()
    people = [db.get(Person, i.person_id) for i in items if i.person_id]
    if reveal:
        charge(db, user, "export", ref=f"list:{lid}", amount=len(people))
    data = [_person_row(p, db, reveal) for p in people if p]
    return StreamingResponse(_csv_stream(PERSON_COLS, data), media_type="text/csv", headers={"content-disposition": f"attachment; filename=list-{lid}.csv"})


@router.api_route("/people/export.csv", methods=["GET", "POST"])
async def export_search(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Export a search result set (same filters as api_search). reveal=true charges 1 credit/row and fills emails."""
    p = await collect_params(request)
    reveal = (p.get("reveal") or ["false"])[0].lower() in ("true", "1")
    limit = min(int((p.get("limit") or ["1000"])[0]), 10000)
    rows = people_query(db, p).order_by(Person.id).limit(limit).all()
    if reveal:
        charge(db, user, "export", ref="search", amount=len(rows))
    data = (_person_row(r, db, reveal) for r in rows)
    return StreamingResponse(_csv_stream(PERSON_COLS, data), media_type="text/csv", headers={"content-disposition": "attachment; filename=people.csv"})
