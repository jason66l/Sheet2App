"""Formula engine: parsing, evaluation, and agreement with the numbers Excel saved."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest

from backend.core import compute
from backend.core.contracts import Record
from backend.core.demo_values import display_rows
from backend.core.engine.evaluate import Evaluator, ExprError, check, parse, recompute
from backend.core.parse import parse_workbook
from backend.spec.models import AppSpec

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (ROOT / "samples" / "Event_Budget_2026.xlsx").read_bytes()
SPEC = AppSpec.model_validate(json.loads((ROOT / "fixtures" / "event_budget.json").read_text()))
TRACKER = AppSpec.model_validate(json.loads((ROOT / "fixtures" / "expense_tracker.json").read_text()))


def sample_rows():
    return display_rows(SPEC, parse_workbook(SAMPLE))


def ev(expr, rows=None, row=None, spec=SPEC):
    rows = rows if rows is not None else {}
    return Evaluator(spec, rows).eval(parse(expr), row, None)


# ---------------------------------------------------------------- language


def test_precedence_and_decimal_math():
    assert ev("1 + 2 * 3") == 7
    assert ev("(1 + 2) * 3") == 9
    assert ev("0.1 + 0.2") == Decimal("0.3")  # exact, unlike float
    assert ev("-2 - -3") == 1
    assert ev("10 / 4") == Decimal("2.5")


def test_comparisons_logic_and_functions():
    assert ev('1 < 2 and not (2 == 3)') is True
    assert ev('"Venue" == "  venue "') is True  # text compares ignoring case/spaces
    assert ev("if(0 == 0, 5, 1 / 0)") == 5  # only the chosen branch runs
    assert ev("round(2.345, 2)") == Decimal("2.35") or ev("round(2.345, 2)") == Decimal("2.34")
    assert ev("max(1, 7, 3)") == 7 and ev("abs(-4)") == 4


def test_bad_expressions_are_reported():
    assert check("budget - ") is not None
    assert check('sum(Expense.amount where state == "approved")') is None
    with pytest.raises(ExprError):
        ev("1 / 0")
    with pytest.raises(ExprError):
        ev("budget")  # a field name needs a record


# ---------------------------------------------------------------- against the sample file


def test_matches_what_excel_saved():
    excel = sample_rows()
    ours = copy.deepcopy(excel)
    _, errors = recompute(SPEC, ours)
    assert errors == []
    for saved, mine in zip(excel["BudgetLine"], ours["BudgetLine"]):
        for name in ("approved", "pending", "remaining"):
            assert Decimal(str(saved[name])) == Decimal(mine[name]), (saved["line"], name)


def test_kpis_match_the_sheet():
    kpis, _ = recompute(SPEC, sample_rows())
    vals = set(kpis.values())
    assert {"4800.00", "2935.40", "612.00", "1252.60"} <= vals


# ---------------------------------------------------------------- live updates


def test_approving_an_expense_moves_money_from_pending_to_approved():
    rows = sample_rows()
    pending_exp = next(r for r in rows["Expense"] if r["__state__"] == "submitted")
    line = next(r for r in rows["BudgetLine"] if r["line"].casefold() == str(pending_exp["budget_line"]).casefold())
    recompute(SPEC, rows)
    before_pending, before_approved = Decimal(line["pending"]), Decimal(line["approved"])

    pending_exp["__state__"] = "approved"
    recompute(SPEC, rows)
    amt = Decimal(str(pending_exp["amount"]))
    assert Decimal(line["pending"]) == before_pending - amt
    assert Decimal(line["approved"]) == before_approved + amt


def test_new_submitted_expense_lowers_remaining():
    rows = sample_rows()
    recompute(SPEC, rows)
    venue = rows["BudgetLine"][0]
    before = Decimal(venue["remaining"])
    rows["Expense"].append({"budget_line": venue["line"], "amount": "100", "__state__": "submitted"})
    kpis, _ = recompute(SPEC, rows)
    assert Decimal(venue["remaining"]) == before - 100


def test_rejected_expense_counts_nowhere():
    rows = {"Category": [{"category": "Travel", "monthly_limit": "500"}],
            "Expense": [{"category": "travel", "amount": "80", "__state__": "rejected"}]}
    recompute(TRACKER, rows)
    cat = rows["Category"][0]
    assert (cat["spent"], cat["pending"], cat["left"]) == ("0.00", "0.00", "500.00")


def test_self_reference_is_caught_not_infinite():
    data = json.loads((ROOT / "fixtures" / "event_budget.json").read_text())
    for e in data["entities"]:
        for c in e.get("computed", []):
            if c["name"] == "remaining":
                c["expr"] = "remaining + 1"
    spec = AppSpec.model_validate(data)
    rows = {"BudgetLine": [{"line": "A", "budget": "10", "remaining": "3"}], "Expense": []}
    _, errors = recompute(spec, rows)
    assert any("depends on itself" in e for e in errors)
    assert rows["BudgetLine"][0]["remaining"] == "3"  # keeps the old value


def test_compute_contract():
    recs = [
        Record(id="b1", entity="BudgetLine", data={"line": "Venue", "budget": "1000"}),
        Record(id="e1", entity="Expense", data={"budget_line": "Venue", "amount": "250"}, state="approved"),
    ]
    res = compute(SPEC, recs)
    assert res.per_record["b1"]["approved"] == "250.00"
    assert res.per_record["b1"]["remaining"] == "750.00"
    assert res.per_record["e1"] == {}
