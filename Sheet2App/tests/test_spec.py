import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend import core
from backend.core.contracts import Record, User
from backend.spec.models import AppSpec, Role

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def raw(name):
    return json.loads((FIX / f"{name}.json").read_text())


@pytest.mark.parametrize("name", ["event_budget", "expense_tracker"])
def test_fixtures_validate(name):
    spec = AppSpec.model_validate(raw(name))
    assert spec.approval_rule is not None


def test_round_trip():
    spec = core.load_fixture("event_budget")
    again = AppSpec.model_validate_json(spec.model_dump_json())
    assert again == spec


def test_rule_tiers():
    r = core.load_fixture("event_budget").approval_rule
    assert r.required_approvals(Decimal("200.00")) == 1   # "over $200" is strict
    assert r.required_approvals(Decimal("200.01")) == 2
    assert r.required_approvals(Decimal("240")) == 2


def _break(mutate):
    d = raw("event_budget")
    mutate(d)
    with pytest.raises(ValidationError) as e:
        AppSpec.model_validate(d)
    return str(e.value)


def test_bad_ref_entity():
    def m(d): d["entities"][1]["fields"][2]["ref_entity"] = "Budget"
    assert "ref_entity 'Budget' does not exist" in _break(m)


def test_unknown_field_in_expr():
    def m(d): d["entities"][0]["computed"][0]["expr"] = "sum(Expense.amt where state == \"approved\")"
    assert "unknown field 'Expense.amt'" in _break(m)


def test_enum_without_options():
    def m(d): d["entities"][1]["fields"][1]["type"] = "enum"
    assert "needs options" in _break(m)


def test_view_unknown_column():
    def m(d): d["views"][3]["columns"].append("vendor")
    assert "unknown field 'Expense.vendor'" in _break(m)


def test_computed_field_in_form():
    def m(d): d["views"][4]["entity"] = "BudgetLine"; d["views"][4]["fields"] = ["line", "remaining"]
    assert "computed fields can't be form inputs" in _break(m)


def test_extra_keys_rejected():
    def m(d): d["entities"][0]["colour"] = "blue"
    _break(m)


def test_stubs_return_contract_types(monkeypatch):
    # run_import is real now: give it the sample file and a fake AI answer (no network).
    from pathlib import Path

    from backend.core.ai import propose

    root = Path(__file__).resolve().parents[1]
    fixture = json.loads((root / "fixtures" / "event_budget.json").read_text())
    monkeypatch.setattr(propose, "generate_json", lambda *a: fixture)
    res = core.run_import((root / "samples" / "Event_Budget_2026.xlsx").read_bytes())
    assert res.proposal.name == "Spring Showcase Budget"
    spec = res.proposal
    rec = Record(id="r1", entity="Expense", data={"amount": "240"}, state="submitted")
    out = core.apply_action(spec, rec, User(id="u1", name="Kai Patel", role=Role.admin), "approve")
    assert out.version == 2
    assert core.compute(spec, [rec]).per_record == {"r1": {}}
    assert core.propose_edit(spec, "require 3 approvals").draft_spec == spec
