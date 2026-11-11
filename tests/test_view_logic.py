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


# ---------------------------------------------------------------- budget management

from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402

from backend.app.view_logic import add_funds, budget_field, duplicate_name, roles_to_create  # noqa: E402


def test_only_admins_add_budget_lines_but_everyone_submits_expenses():
    assert roles_to_create(SPEC, "BudgetLine") == {"admin"}
    assert roles_to_create(SPEC, "Expense") == {"admin", "approver", "submitter"}


def test_budget_field_comes_from_the_budget_table_view():
    assert budget_field(SPEC, "BudgetLine") == "budget"
    assert budget_field(SPEC, "Expense") is None


def test_duplicate_budget_line_names_are_refused():
    existing = [{"line": "Venue", "budget": "1500"}]
    assert duplicate_name(SPEC, "BudgetLine", {"line": " venue "}, existing)
    assert duplicate_name(SPEC, "BudgetLine", {"line": "Prizes"}, existing) is None
    assert duplicate_name(SPEC, "Expense", {"description": "Venue"}, [{"description": "Venue"}]) is None


def test_add_funds_raises_budget_and_logs_it():
    data = {"line": "Food", "budget": "800"}
    out = add_funds(data, "budget", Decimal("500"), "Bake sale", ME, "Jason", "2026-11-10T20:00:00Z")
    assert out["budget"] == "1300.00"
    assert out["_funds"] == [{"amount": "500.00", "note": "Bake sale", "by_id": ME, "by": "Jason", "at": "2026-11-10T20:00:00Z"}]
    out = add_funds(out, "budget", Decimal("-50"), "Typo fix", ME, "Jason", "t2")
    assert out["budget"] == "1250.00" and len(out["_funds"]) == 2
    assert data == {"line": "Food", "budget": "800"}  # original untouched


def test_add_funds_rejects_bad_input():
    with pytest.raises(ValueError):
        add_funds({"budget": "100"}, "budget", Decimal("0"), "x", ME, "J", "t")
    with pytest.raises(ValueError):
        add_funds({"budget": "100"}, "budget", Decimal("10"), "  ", ME, "J", "t")
    with pytest.raises(ValueError):
        add_funds({"budget": "100"}, "budget", Decimal("-101"), "oops", ME, "J", "t")


def test_funding_history_shows_on_rows():
    rows = build_rows(SPEC, [{"id": "b1", "entity": "BudgetLine", "state": None,
                              "data": {"line": "Food", "budget": "1300", "_funds": [{"amount": "500.00"}]}}], {})
    r = rows["BudgetLine"][0]
    assert r["__funds__"] == [{"amount": "500.00"}] and "_funds" not in r
