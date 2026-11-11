"""Saved apps: open one, add records, approve/reject, invite people.

Every route checks the caller's membership and role on the server, so the rules
hold even if someone bypasses the frontend:
- admin: everything, plus invites, new budget lines and adding funds
- approver: approve/reject and submit
- submitter: submit and view
- nobody approves their own request, and each person approves a request once
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import tables
from backend.app.auth import AuthUser, current_user
from backend.app.db import get_db
from backend.app.profiles import upsert_profile
from backend.app.view_logic import (
    CAN_APPROVE, CAN_INVITE, CAN_MANAGE_BUDGET, add_funds, approval_result, approve_blocker,
    budget_field, build_rows, default_user_fields, duplicate_name, roles_to_create,
)
from backend.core.demo_values import kpi_values
from backend.spec.models import AppSpec

router = APIRouter(tags=["apps"])

INVITE_DAYS = 14


def require_role(db: Session, app_id: uuid.UUID, user: AuthUser, roles: set[str] | tuple[str, ...] = tables.ROLES) -> str:
    """Return the caller's role in the app, or 404 if they are not a member.

    404 rather than 403, so outsiders can't tell whether an app id exists.
    """
    role = db.scalar(
        select(tables.Membership.role).where(
            tables.Membership.app_id == app_id, tables.Membership.user_id == uuid.UUID(user.id)
        )
    )
    if role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "App not found")
    if role not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Your role ({role}) can't do this.")
    return role


def _spec(app_row: tables.App) -> AppSpec:
    return AppSpec.model_validate(app_row.spec)


# ------------------------------------------------------------------- read


@router.get("/apps/{app_id}/view")
def app_view(app_id: uuid.UUID, user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Everything the app screen needs: spec, rows (with approvals), KPI values, my role."""
    role = require_role(db, app_id, user)
    app_row = db.get(tables.App, app_id)
    assert app_row is not None
    spec = _spec(app_row)

    records = db.scalars(
        select(tables.Record).where(tables.Record.app_id == app_id).order_by(tables.Record.created_at)
    ).all()
    approvals = db.execute(
        select(tables.Approval.record_id, tables.Approval.approver_id, tables.Profile.name, tables.Profile.email)
        .join(tables.Profile, tables.Profile.id == tables.Approval.approver_id)
        .join(tables.Record, tables.Record.id == tables.Approval.record_id)
        .where(tables.Record.app_id == app_id, tables.Approval.decision == "approve")
        .order_by(tables.Approval.created_at)
    ).all()
    names: dict[str, list[str]] = {}
    approver_ids: dict[str, list[str]] = {}
    for a in approvals:
        names.setdefault(str(a.record_id), []).append(a.name or a.email or "Member")
        approver_ids.setdefault(str(a.record_id), []).append(str(a.approver_id))

    rows = build_rows(
        spec,
        [{"id": r.id, "entity": r.entity, "data": r.data, "state": r.state} for r in records],
        names,
    )
    # Tell the screen which rows this user may act on, so buttons can be hidden or explained.
    by_id = {str(r.id): r for r in records}
    for entity_rows in rows.values():
        for row in entity_rows:
            rec = by_id[row["__id__"]]
            row["__mine__"] = rec.created_by is not None and str(rec.created_by) == user.id
            row["__blocked__"] = approve_blocker(
                role, user.id, str(rec.created_by) if rec.created_by else None, rec.state,
                approver_ids.get(row["__id__"], []),
            )

    # Recompute every computed column and KPI tile from the current records (in place),
    # so approving or submitting an expense changes the numbers right away.
    kpis = kpi_values(spec, rows)

    source = db.scalar(select(tables.Import.file_name).where(tables.Import.app_id == app_id))
    return {
        "app_id": str(app_id),
        "role": role,
        "file_name": source or app_row.name,
        "created_at": app_row.created_at.isoformat(),
        "spec": app_row.spec,
        "rows": rows,
        "kpis": kpis,
    }


# ------------------------------------------------------------------ write


class NewRecord(BaseModel):
    entity: str
    data: dict[str, Any]


@router.post("/apps/{app_id}/records", status_code=status.HTTP_201_CREATED)
def create_record(app_id: uuid.UUID, body: NewRecord, user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    role = require_role(db, app_id, user)
    app_row = db.get(tables.App, app_id)
    assert app_row is not None
    spec = _spec(app_row)
    ent = spec.entity(body.entity)
    if ent is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown table {body.entity}")
    if role not in roles_to_create(spec, body.entity):
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Only admins can add {ent.label.lower()}.")

    allowed = {f.name for f in ent.fields}
    data = {k: v for k, v in body.data.items() if k in allowed}  # ignore anything not in the spec
    missing = [f.label for f in ent.fields if f.required and not data.get(f.name) and f.type.value != "user"]
    if missing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Missing: {', '.join(missing)}")
    data = default_user_fields(spec, body.entity, data, user.name or user.email or "Member")
    existing = db.scalars(
        select(tables.Record.data).where(tables.Record.app_id == app_id, tables.Record.entity == body.entity)
    ).all()
    dup = duplicate_name(spec, body.entity, data, list(existing))
    if dup:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, dup)

    upsert_profile(db, user)
    rec = tables.Record(
        app_id=app_id, entity=body.entity, data=data,
        state="submitted" if ent.workflow else None, created_by=uuid.UUID(user.id),
    )
    db.add(rec)
    db.flush()
    db.commit()  # save before replying; the next request may read it right away
    return {"id": str(rec.id)}


class Decision(BaseModel):
    comment: str | None = None


def _decide(record_id: uuid.UUID, decision: str, body: Decision, user: AuthUser, db: Session) -> dict:
    rec = db.get(tables.Record, record_id)
    if rec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    role = require_role(db, rec.app_id, user)  # 404 for non-members
    already = [
        str(a) for a in db.scalars(
            select(tables.Approval.approver_id).where(
                tables.Approval.record_id == rec.id, tables.Approval.decision == "approve"
            )
        )
    ]
    blocker = approve_blocker(role, user.id, str(rec.created_by) if rec.created_by else None, rec.state, already)
    if blocker:
        raise HTTPException(status.HTTP_403_FORBIDDEN, blocker)

    upsert_profile(db, user)
    db.add(tables.Approval(
        record_id=rec.id, approver_id=uuid.UUID(user.id), decision=decision,
        comment=body.comment, record_version=rec.version,
    ))
    if decision == "reject":
        rec.state = "rejected"
        rec.version += 1
        db.commit()  # save before replying; the next request may read it right away
        return {"state": rec.state}

    app_row = db.get(tables.App, rec.app_id)
    assert app_row is not None
    given, needed, new_state = approval_result(_spec(app_row), rec.entity, rec.data, len(already))
    if new_state != rec.state:
        rec.state = new_state
        rec.version += 1
    db.commit()  # save before replying; the next request may read it right away
    return {"state": rec.state, "approvals": given, "needed": needed}


@router.post("/records/{record_id}/approve")
def approve(record_id: uuid.UUID, body: Decision | None = None, user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return _decide(record_id, "approve", body or Decision(), user, db)


@router.post("/records/{record_id}/reject")
def reject(record_id: uuid.UUID, body: Decision | None = None, user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return _decide(record_id, "reject", body or Decision(), user, db)


class NewFunds(BaseModel):
    amount: Decimal
    note: str = ""


@router.post("/records/{record_id}/funds")
def record_funds(record_id: uuid.UUID, body: NewFunds, user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Admin adds money to a budget line (or a negative amount to fix a mistake). Logged on the line."""
    rec = db.get(tables.Record, record_id)
    if rec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Budget line not found")
    require_role(db, rec.app_id, user, CAN_MANAGE_BUDGET)
    app_row = db.get(tables.App, rec.app_id)
    assert app_row is not None
    field = budget_field(_spec(app_row), rec.entity)
    if field is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Funds can only be added to budget lines.")
    upsert_profile(db, user)
    try:
        rec.data = add_funds(
            rec.data, field, body.amount, body.note, user.id, user.name or user.email or "Admin",
            datetime.now(UTC).isoformat(),
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    rec.version += 1
    db.commit()  # save before replying; the page reloads right after
    return {"id": str(rec.id), field: rec.data[field]}


# ---------------------------------------------------------------- members


class NewInvite(BaseModel):
    role: str = "submitter"


@router.post("/apps/{app_id}/invites", status_code=status.HTTP_201_CREATED)
def create_invite(app_id: uuid.UUID, body: NewInvite, user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    require_role(db, app_id, user, CAN_INVITE)
    if body.role not in tables.ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Role must be one of {', '.join(tables.ROLES)}")
    token = secrets.token_urlsafe(16)
    db.add(tables.Invite(
        token=token, app_id=app_id, role=body.role, created_by=uuid.UUID(user.id),
        expires_at=datetime.now(UTC) + timedelta(days=INVITE_DAYS),
    ))
    db.commit()  # save before replying; the next request may read it right away
    return {"token": token, "role": body.role, "expires_in_days": INVITE_DAYS}


@router.post("/invites/{token}/accept")
def accept_invite(token: str, user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    inv = db.get(tables.Invite, token)
    if inv is None or inv.expires_at < datetime.now(UTC):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This invite link is invalid or has expired.")
    upsert_profile(db, user)
    me = uuid.UUID(user.id)
    existing = db.get(tables.Membership, {"app_id": inv.app_id, "user_id": me})
    if existing is None:
        db.add(tables.Membership(app_id=inv.app_id, user_id=me, role=inv.role))
        role = inv.role
    else:
        role = existing.role  # never downgrade someone who is already a member
    db.commit()  # save before replying; the next request may read it right away
    return {"app_id": str(inv.app_id), "role": role}


@router.get("/apps/{app_id}/members")
def members(app_id: uuid.UUID, user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    require_role(db, app_id, user)
    rows = db.execute(
        select(tables.Profile.id, tables.Profile.name, tables.Profile.email, tables.Membership.role)
        .join(tables.Membership, tables.Membership.user_id == tables.Profile.id)
        .where(tables.Membership.app_id == app_id)
        .order_by(tables.Membership.created_at)
    ).all()
    return [{"id": str(r.id), "name": r.name, "email": r.email, "role": r.role} for r in rows]


@router.patch("/apps/{app_id}/members/{member_id}")
def change_role(app_id: uuid.UUID, member_id: uuid.UUID, body: NewInvite, user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    require_role(db, app_id, user, CAN_INVITE)
    if body.role not in tables.ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Role must be one of {', '.join(tables.ROLES)}")
    if str(member_id) == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't change your own role.")
    m = db.get(tables.Membership, {"app_id": app_id, "user_id": member_id})
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    m.role = body.role
    db.commit()  # save before replying; the next request may read it right away
    return {"id": str(member_id), "role": m.role}


__all__ = ["router", "require_role", "CAN_APPROVE"]
