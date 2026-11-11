"""Values the demo screen shows, before the real formula engine exists.

TEMPORARY. The real numbers come from compute() once Julian's evaluator lands
(weeks 6-8). Until then:
- computed columns show the values Excel last saved (rows.computed_from_sheet)
- KPI tiles support only sums and counts, e.g.
    sum(BudgetLine.budget)
    sum(BudgetLine.budget) - sum(BudgetLine.approved)
    sum(Expense.amount where state == "approved")
    count(Expense where state == "submitted")
  Anything else shows as None (the screen prints a dash).
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from backend.core.parse import ParsedWorkbook
from backend.core.rows import computed_from_sheet, rows_for_entities
from backend.spec.models import AppSpec

_TERM = re.compile(
    r"""\s*([+-])?\s*
        (sum|count)\(\s*([A-Z][A-Za-z0-9]*)(?:\.([a-z][a-z0-9_]*))?
        (?:\s+where\s+state\s*==\s*["']([a-z_]+)["'])?\s*\)\s*""",
    re.X,
)


def _dec(v: Any) -> Decimal:
    try:
        return Decimal(str(v)) if v not in (None, "") else Decimal(0)
    except InvalidOperation:
        return Decimal(0)


def display_rows(spec: AppSpec, parsed: ParsedWorkbook) -> dict[str, list[dict[str, Any]]]:
    """Field values plus Excel's saved values for computed columns, one dict per row."""
    rows = rows_for_entities(spec, parsed)
    computed = computed_from_sheet(spec, parsed)
    for entity, extra in computed.items():
        for row, values in zip(rows.get(entity, []), extra):
            row.update(values)
    return rows


def eval_tile(expr: str, rows: dict[str, list[dict[str, Any]]]) -> str | None:
    """Evaluate a KPI expression made only of sum()/count() terms joined by + or -."""
    pos, total, matched = 0, Decimal(0), False
    while pos < len(expr):
        m = _TERM.match(expr, pos)
        if not m or (matched and not m.group(1)):
            return None
        sign, fn, entity, field, state = m.groups()
        items = [r for r in rows.get(entity, []) if state is None or r.get("__state__") == state]
        value = Decimal(len(items)) if fn == "count" else sum((_dec(r.get(field)) for r in items), Decimal(0))
        total = total - value if sign == "-" else total + value
        pos, matched = m.end(), True
    return str(total) if matched else None


def kpi_values(spec: AppSpec, rows: dict[str, list[dict[str, Any]]]) -> dict[str, str | None]:
    """{view_id: {tile_label: value}} flattened to "view_id/label" keys."""
    out: dict[str, str | None] = {}
    for view in spec.views:
        if view.type == "kpi":
            for tile in view.tiles:
                out[f"{view.id}/{tile.label}"] = eval_tile(tile.expr, rows)
    return out
