"""run_import pipeline on the sample workbook. The LLM is faked: no network, no API key."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.core import run_import
from backend.core.ai import propose
from backend.core.ai.client import LLMError
from backend.core.parse import parse_workbook

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (ROOT / "samples" / "Event_Budget_2026.xlsx").read_bytes()
FIXTURE = json.loads((ROOT / "fixtures" / "event_budget.json").read_text())


def test_parse_finds_tables_formulas_and_rule_note():
    parsed = parse_workbook(SAMPLE)
    by_sheet = {t.sheet: t for t in parsed.tables}
    assert len(by_sheet["Budget"].rows) == 6          # Total row excluded
    assert len(by_sheet["Expenses"].rows) == 11
    remaining = next(c for c in by_sheet["Budget"].columns if c.header == "Remaining")
    assert remaining.formula == "=B{r}-C{r}-D{r}"
    status = next(c for c in by_sheet["Expenses"].columns if c.header == "Status")
    assert status.type == "enum" and status.options == ["Pending", "Approved", "Rejected"]
    assert any("over $200" in n["text"] for n in parsed.notes)
    assert parsed.formula_cells == 29


def test_money_is_never_a_float():
    parsed = parse_workbook(SAMPLE)
    food = parsed.tables[0].rows[1]
    assert food["Approved"] == "742.4"                  # string, converted via Decimal


def test_run_import_uses_ai_proposal_and_maps_rows(monkeypatch):
    calls = []
    monkeypatch.setattr(propose, "generate_json", lambda system, user, schema=None: calls.append(user) or FIXTURE)
    result = run_import(SAMPLE)

    assert len(calls) == 1
    assert "over $200" in calls[0]                      # the note reached the prompt
    assert result.proposal.name == FIXTURE["name"]
    expenses = result.rows["Expense"]
    assert len(expenses) == 11
    assert expenses[-1]["__state__"] == "submitted"     # Pending -> submitted
    assert expenses[0]["__approved_by__"] == ["Kai Patel", "Priya Shah"]
    assert not any(w.startswith("AI step failed") for w in result.warnings)


def test_invalid_answer_is_retried_once(monkeypatch):
    answers = iter([{"name": "broken"}, FIXTURE])
    monkeypatch.setattr(propose, "generate_json", lambda *a: next(answers))
    assert run_import(SAMPLE).proposal.name == FIXTURE["name"]


def test_ai_failure_falls_back_to_fixture(monkeypatch):
    def boom(*a):
        raise LLMError("quota exceeded")

    monkeypatch.setattr(propose, "generate_json", boom)
    result = run_import(SAMPLE)
    assert result.proposal.name == FIXTURE["name"]
    assert result.warnings[0].startswith("AI step failed")


def test_not_a_spreadsheet_is_rejected():
    with pytest.raises(ValueError):
        run_import(b"not an xlsx file")
