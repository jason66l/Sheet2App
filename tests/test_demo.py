"""Demo display values and the proposal cache. No network."""

from __future__ import annotations

import json
from pathlib import Path

from backend.core import cache, run_import
from backend.core.ai import propose
from backend.core.demo_values import display_rows, eval_tile, kpi_values
from backend.core.parse import parse_workbook
from backend.spec.models import AppSpec

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (ROOT / "samples" / "Event_Budget_2026.xlsx").read_bytes()
FIXTURE = json.loads((ROOT / "fixtures" / "event_budget.json").read_text())
SPEC = AppSpec.model_validate(FIXTURE)


def test_display_rows_include_excel_values_for_computed_columns():
    rows = display_rows(SPEC, parse_workbook(SAMPLE))
    food = rows["BudgetLine"][1]
    assert food["line"] == "Food & drinks"
    assert food["remaining"] == "217.6"
    assert rows["Expense"][-1]["__state__"] == "submitted"


def test_kpi_sums_counts_and_differences():
    rows = display_rows(SPEC, parse_workbook(SAMPLE))
    assert eval_tile("sum(BudgetLine.budget)", rows) == "4800"
    assert eval_tile("sum(BudgetLine.budget) - sum(BudgetLine.approved) - sum(BudgetLine.pending)", rows) == "1252.6"
    assert eval_tile('sum(Expense.amount where state == "submitted")', rows) == "612"
    assert eval_tile('count(Expense where state == "submitted")', rows) == "2"
    assert eval_tile("budget * 2", rows) is None  # unsupported -> dash on screen
    assert all(isinstance(k, str) for k in kpi_values(SPEC, rows))


def test_cache_makes_second_import_skip_the_ai(monkeypatch):
    monkeypatch.setenv("PROPOSAL_CACHE", "1")
    calls = []
    monkeypatch.setattr(propose, "generate_json", lambda *a, **k: calls.append(1) or FIXTURE)
    run_import(SAMPLE)
    run_import(SAMPLE)
    assert len(calls) == 1


def test_cache_off_by_default():
    assert not cache.enabled()
