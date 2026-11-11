"""FastAPI entry point.

Run from the repo root:
    uv run uvicorn backend.app.main:app --reload
"""

from __future__ import annotations

import uuid

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import tables
from backend.app.auth import AuthUser, current_user
from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.profiles import upsert_profile
from backend.app.routes import apps, imports

app = FastAPI(title="Sheet2App API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().frontend_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(imports.router)
app.include_router(apps.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/me")
def me(user: AuthUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Who am I, and which apps can I open? Also creates my profile on first sign-in."""
    upsert_profile(db, user)
    rows = db.execute(
        select(tables.App.id, tables.App.name, tables.Membership.role)
        .join(tables.Membership, tables.Membership.app_id == tables.App.id)
        .where(tables.Membership.user_id == uuid.UUID(user.id))
        .order_by(tables.App.created_at.desc())
    ).all()
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "apps": [{"id": str(r.id), "name": r.name, "role": r.role} for r in rows],
    }
