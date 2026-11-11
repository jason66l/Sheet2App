"""Person A's public surface. B calls only these four functions.

Week 1: every function is a stub that returns fixture data, so B can build
routes and screens before any real logic exists. Each stub is replaced in the
week noted, keeping the same signature.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.core.contracts import (
    ComputeResult, EditProposal, ImportResult, Reconciliation, Record, User,
)
from backend.spec.models import AppSpec

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
log = logging.getLogger("sheet2app.core")


def load_fixture(name: str) -> AppSpec:
    return AppSpec.model_validate_json((FIXTURES / f"{name}.json").read_text())


def run_import(file_bytes: bytes) -> ImportResult:
    """Spreadsheet -> parse -> digest -> Gemini proposes an AppSpec -> rows mapped onto it.

    Reconciliation (recomputing every formula and comparing to Excel) lands in weeks 6-8;
    until then it reports how many formula cells were found, with 0 translated.

    If anything in the AI step fails, falls back to the event_budget fixture with a
    warning, so a demo never ends on an error screen.
    """
    # Imported here so the stubs below still work without the google-genai package installed.
    from backend.core import cache
    from backend.core.ai.propose import propose_spec
    from backend.core.digest import make_digest
    from backend.core.parse import parse_workbook
    from backend.core.rows import rows_for_entities

    try:
        parsed = parse_workbook(file_bytes)
    except Exception as exc:  # not a readable .xlsx
        raise ValueError(f"Could not read this spreadsheet: {exc}") from exc

    digest = make_digest(parsed, file_bytes)
    reconciliation = Reconciliation(formulas_total=parsed.formula_cells, formulas_translated=0, matched=0)
    warnings = ["Totals check against your file is not built yet (weeks 6-8)."]

    proposal = cache.get(digest.workbook_sha256)  # only when PROPOSAL_CACHE=1
    if proposal is None:
        try:
            proposal = propose_spec(digest)
            cache.put(digest.workbook_sha256, proposal)
        except Exception as exc:  # noqa: BLE001 - any AI failure falls back to the fixture
            log.exception("AI proposal failed; falling back to fixture")
            proposal = load_fixture("event_budget")
            warnings.insert(0, f"AI step failed, showing the sample app instead: {str(exc)[:200]}")

    return ImportResult(
        digest=digest,
        proposal=proposal,
        reconciliation=reconciliation,
        rows=rows_for_entities(proposal, parsed),
        warnings=warnings,
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
