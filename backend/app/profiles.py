"""Keep a profiles row for every signed-in user (foreign keys point at it)."""

from __future__ import annotations

import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.app import tables
from backend.app.auth import AuthUser


def upsert_profile(db: Session, user: AuthUser) -> None:
    stmt = insert(tables.Profile).values(id=uuid.UUID(user.id), email=user.email, name=user.name)
    db.execute(stmt.on_conflict_do_update(
        index_elements=[tables.Profile.id],
        set_={"email": stmt.excluded.email, "name": stmt.excluded.name},
    ))
