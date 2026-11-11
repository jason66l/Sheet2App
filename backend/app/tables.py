"""Database tables. Alembic migrations in backend/migrations are generated from these.

Change a table here, then run:
    uv run alembic revision --autogenerate -m "describe the change"
    uv run alembic upgrade head
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ROLES = ("admin", "approver", "submitter")


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSONB, list[str]: JSONB, uuid.UUID: UUID(as_uuid=True)}


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Profile(Base):
    """One row per signed-in person. id is the Supabase auth user id."""

    __tablename__ = "profiles"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    email: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _now()


class App(Base):
    __tablename__ = "apps"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    spec: Mapped[dict[str, Any]] = mapped_column(nullable=False)
    previous_spec: Mapped[dict[str, Any] | None] = mapped_column()
    created_at: Mapped[datetime] = _now()


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (CheckConstraint(f"role in {ROLES}", name="membership_role_valid"),)
    app_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = _now()


class Invite(Base):
    __tablename__ = "invites"
    __table_args__ = (CheckConstraint(f"role in {ROLES}", name="invite_role_valid"),)
    token: Mapped[str] = mapped_column(Text, primary_key=True)
    app_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    created_at: Mapped[datetime] = _now()


class Import(Base):
    """One uploaded spreadsheet and what run_import() made of it."""

    __tablename__ = "imports"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)  # path inside the storage bucket
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="processing")
    error: Mapped[str | None] = mapped_column(Text)
    digest: Mapped[dict[str, Any] | None] = mapped_column()
    proposal: Mapped[dict[str, Any] | None] = mapped_column()
    reconciliation: Mapped[dict[str, Any] | None] = mapped_column()
    rows: Mapped[dict[str, Any] | None] = mapped_column()
    warnings: Mapped[list[str] | None] = mapped_column()
    app_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("apps.id"))  # set on confirm
    created_at: Mapped[datetime] = _now()


class Record(Base):
    __tablename__ = "records"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    app_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(nullable=False)
    state: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id"))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (CheckConstraint("decision in ('approve', 'reject')", name="approval_decision_valid"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("records.id", ondelete="CASCADE"), nullable=False, index=True)
    approver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(8), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    record_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = _now()


ALL_TABLES = [t.name for t in Base.metadata.sorted_tables]
