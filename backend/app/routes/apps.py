"""Read an app. Every route checks the caller is a member of the app."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import tables
from backend.app.auth import AuthUser, current_user
from backend.app.db import get_db

router = APIRouter(prefix="/apps", tags=["apps"])


def require_role(db: Session, app_id: uuid.UUID, user: AuthUser, roles: tuple[str, ...] = tables.ROLES) -> str:
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
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {', '.join(roles)}")
    return role


@router.get("/{app_id}/spec")
def get_spec(app_id: uuid.UUID, user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    role = require_role(db, app_id, user)
    app_row = db.get(tables.App, app_id)
    assert app_row is not None
    return {"id": str(app_row.id), "name": app_row.name, "role": role, "spec": app_row.spec}


@router.get("/{app_id}/records")
def list_records(
    app_id: uuid.UUID, entity: str | None = None,
    user: AuthUser = Depends(current_user), db: Session = Depends(get_db),
) -> list[dict]:
    require_role(db, app_id, user)
    q = select(tables.Record).where(tables.Record.app_id == app_id).order_by(tables.Record.created_at)
    if entity:
        q = q.where(tables.Record.entity == entity)
    return [
        {"id": str(r.id), "entity": r.entity, "data": r.data, "state": r.state, "version": r.version}
        for r in db.scalars(q)
    ]
