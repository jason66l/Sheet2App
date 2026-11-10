"""Person A's public surface. B calls only these four functions.

Week 1: every function is a stub that returns fixture data, so B can build
routes and screens before any real logic exists. Each stub is replaced in the
week noted, keeping the same signature.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from backend.core.contracts import (
    ComputeResult, EditProposal, ImportResult, Reconciliation, Record, SheetDigest, User,
)
from backend.spec.models import AppSpec

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def load_fixture(name: str) -> AppSpec:
    return AppSpec.model_validate_json((FIXTURES / f"{name}.json").read_text())


def run_import(file_bytes: bytes) -> ImportResult:
    """Real version: weeks 2-5 (parse -> digest -> propose), reconciliation weeks 6-8."""
    return ImportResult(
        digest=SheetDigest(workbook_sha256=hashlib.sha256(file_bytes).hexdigest(), sheets=[]),
        proposal=load_fixture("event_budget"),
        reconciliation=Reconciliation(formulas_total=29, formulas_translated=29, matched=29),
        warnings=["stub: returning fixtures/event_budget.json"],
    )


def compute(spec: AppSpec, records: list[Record]) -> ComputeResult:
    """Real version: weeks 6-8. Stub returns no computed values."""
    return ComputeResult(per_record={r.id: {} for r in records}, app={})


def apply_action(spec: AppSpec, record: Record, user: User, action: str,
                 comment: str | None = None) -> Record:
    """Real version: weeks 9-10. Stub just flips the state."""
    to = {"submit": "submitted", "approve": "approved", "reject": "rejected"}[action]
    return record.model_copy(update={"state": to, "version": record.version + 1})


def propose_edit(spec: AppSpec, message: str) -> EditProposal:
    """Real version: weeks 11-12. Stub returns the spec unchanged."""
    return EditProposal(draft_spec=spec, summary="(stub) no change", changed_fields=[])
