"""Initial tables: profiles, apps, memberships, invites, imports, records, approvals.

Also turns on Row Level Security for every table with no policies. Our FastAPI
backend connects as the database owner, so it is not affected. But it blocks
anyone from reading these tables through Supabase's public REST API with the
publishable key.

Revision ID: 0001
Revises:
Create Date: 2026-11-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TABLES = ["profiles", "apps", "memberships", "invites", "imports", "records", "approvals"]
ROLE_CHECK = "role in ('admin', 'approver', 'submitter')"


def _created_at() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text()),
        sa.Column("name", sa.Text()),
        _created_at(),
    )
    op.create_table(
        "apps",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", pg.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("spec", pg.JSONB(), nullable=False),
        sa.Column("previous_spec", pg.JSONB()),
        _created_at(),
    )
    op.create_table(
        "memberships",
        sa.Column("app_id", pg.UUID(as_uuid=True), sa.ForeignKey("apps.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(16), nullable=False),
        _created_at(),
        sa.CheckConstraint(ROLE_CHECK, name="membership_role_valid"),
    )
    op.create_table(
        "invites",
        sa.Column("token", sa.Text(), primary_key=True),
        sa.Column("app_id", pg.UUID(as_uuid=True), sa.ForeignKey("apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=False),
        _created_at(),
        sa.CheckConstraint(ROLE_CHECK, name="invite_role_valid"),
    )
    op.create_table(
        "imports",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", pg.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("digest", pg.JSONB()),
        sa.Column("proposal", pg.JSONB()),
        sa.Column("reconciliation", pg.JSONB()),
        sa.Column("rows", pg.JSONB()),
        sa.Column("warnings", pg.JSONB()),
        sa.Column("app_id", pg.UUID(as_uuid=True), sa.ForeignKey("apps.id")),
        _created_at(),
    )
    op.create_table(
        "records",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("app_id", pg.UUID(as_uuid=True), sa.ForeignKey("apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity", sa.Text(), nullable=False),
        sa.Column("data", pg.JSONB(), nullable=False),
        sa.Column("state", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("profiles.id")),
        _created_at(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_records_app_id", "records", ["app_id"])
    op.create_table(
        "approvals",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("record_id", pg.UUID(as_uuid=True), sa.ForeignKey("records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("approver_id", pg.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("decision", sa.String(8), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("record_version", sa.Integer(), nullable=False),
        _created_at(),
        sa.CheckConstraint("decision in ('approve', 'reject')", name="approval_decision_valid"),
    )
    op.create_index("ix_approvals_record_id", "approvals", ["record_id"])

    for table in TABLES:
        op.execute(f'alter table public."{table}" enable row level security')


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
