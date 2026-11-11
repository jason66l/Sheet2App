"""Saved-app view rows, approval counting and role checks. No database needed."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.view_logic import (
    approval_result, approve_blocker, approvals_needed, build_rows, default_user_fields,
)
from backend.spec.models import AppSpec

SPEC = AppSpec.model_validate_json(
    (Path(__file__).resolve().parents[1] / "fixtures" / "event_budget.json").read_text()
)
ME, OTHER = "user-me", "user-other"


def test_build_rows_merges_imported_and_app_approvers():
    rows = build_rows(
        SPEC,
        [{"id": "r1", "entity": "Expense", "state": "submitted",
          "data": {"description": "Pizza", "amount": "240", "_imported_approved_by": ["Ava Brooks"]}}],
        {"r1": ["Kai Patel"]},
    )
    r = rows["Expense"][0]
    assert r["__id__"] == "r1" and r["__state__"] == "submitted"
    assert r["__approved_by__"] == ["Ava Brooks", "Kai Patel"]
    assert "_imported_approved_by" not in r
    assert rows["BudgetLine"] == []


def test_over_threshold_needs_two_distinct_approvals():
    assert approvals_needed(SPEC, "Expense", {"amount": "240"}) == 2
    assert approvals_needed(SPEC, "Expense", {"amount": "200"}) == 1  # strictly over $200
    assert approval_result(SPEC, "Expense", {"amount": "372"}, 0) == (1, 2, "submitted")
    assert approval_result(SPEC, "Expense", {"amount": "372"}, 1) == (2, 2, "approved")
    # imported approvals count: pizza already had Ava Brooks in the sheet
    assert approval_result(SPEC, "Expense", {"amount": "240", "_imported_approved_by": ["Ava"]}, 0)[2] == "approved"


def test_roles_and_no_self_approval():
    ok = dict(user_id=ME, record_created_by=OTHER, record_state="submitted", already_approved_by=[])
    assert approve_blocker("approver", **ok) is None
    assert approve_blocker("admin", **ok) is None
    assert "Only approvers" in approve_blocker("submitter", **ok)
    assert "your own" in approve_blocker("approver", **{**ok, "record_created_by": ME})
    assert "already approved" in approve_blocker("approver", **{**ok, "already_approved_by": [ME]})
    assert approve_blocker("approver", **{**ok, "record_state": "approved"}).startswith("This request is already")


def test_imported_rows_have_no_creator_so_uploader_can_approve():
    assert approve_blocker("admin", ME, None, "submitted", []) is None


def test_person_fields_default_to_signed_in_user():
    out = default_user_fields(SPEC, "Expense", {"description": "Tape"}, "Jason Lee")
    assert out["submitted_by"] == "Jason Lee"
