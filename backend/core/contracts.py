"""Types that cross the A/B boundary. B's API routes import these."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel

from backend.spec.models import AppSpec, Provenance, Role

Value = str | int | Decimal | None  # money/number as Decimal, dates as ISO strings


class User(BaseModel):
    id: str
    name: str
    role: Role


class Approval(BaseModel):
    approver_id: str
    decision: Literal["approve", "reject"]
    comment: str | None = None
    record_version: int
    at: datetime


class Record(BaseModel):
    id: str
    entity: str
    data: dict[str, Any]
    state: str | None = None
    version: int = 1
    created_by: str | None = None
    # apply_action needs the approvals already given to count them.
    # B loads them from the approvals table and passes them in here.
    approvals: list[Approval] = []


# ---------------------------------------------------------------- import


class SheetDigest(BaseModel):
    """Compact workbook summary sent to the LLM. Filled in during weeks 2-3."""

    workbook_sha256: str
    sheets: list[dict[str, Any]]
    notes: list[dict[str, Any]] = []  # free-text cells outside tables


class Mismatch(BaseModel):
    cell: Provenance
    excel_value: Decimal | None
    our_value: Decimal | None
    reason: Literal["mismatch", "unsupported_formula", "error"]


class Reconciliation(BaseModel):
    formulas_total: int
    formulas_translated: int
    matched: int
    mismatches: list[Mismatch] = []

    @property
    def ok(self) -> bool:
        return not self.mismatches


class ImportResult(BaseModel):
    digest: SheetDigest
    proposal: AppSpec
    reconciliation: Reconciliation
    # Rows read from the workbook, mapped onto proposal entities, so B's
    # /confirm can insert them as records without re-parsing.
    rows: dict[str, list[dict[str, Any]]] = {}
    warnings: list[str] = []


# ---------------------------------------------------------------- compute


class ComputeResult(BaseModel):
    per_record: dict[str, dict[str, Value]]  # record_id -> computed field -> value
    app: dict[str, Value]                    # KPI tile label -> value


# ---------------------------------------------------------------- chat edits


class EditProposal(BaseModel):
    draft_spec: AppSpec | None
    summary: str
    changed_fields: list[str]                # dotted paths, e.g. "approval_rule.threshold"
    clarifying_question: str | None = None   # set instead of draft_spec when ambiguous
