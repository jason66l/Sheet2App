"""Values the app screen shows.

display_rows: field values plus the values Excel saved for computed columns (what the
file said at upload time). kpi_values: recomputes every computed column and KPI tile
from the current records with the formula engine (core/engine/evaluate.py), so numbers
change as soon as an expense is submitted, approved or rejected.
"""

from __future__ import annotations

from typing import Any

from backend.core.parse import ParsedWorkbook
from backend.core.rows import computed_from_sheet, rows_for_entities
from backend.spec.models import AppSpec


def display_rows(spec: AppSpec, parsed: ParsedWorkbook) -> dict[str, list[dict[str, Any]]]:
    """Field values plus Excel's saved values for computed columns, one dict per row."""
    rows = rows_for_entities(spec, parsed)
    computed = computed_from_sheet(spec, parsed)
    for entity, extra in computed.items():
        for row, values in zip(rows.get(entity, []), extra):
            row.update(values)
    return rows


def kpi_values(spec: AppSpec, rows: dict[str, list[dict[str, Any]]]) -> dict[str, str | None]:
    """{"view_id/tile label": value}. Also recomputes every computed column on rows, in place,
    so the table and the tiles always agree with the current records."""
    from backend.core.engine.evaluate import recompute

    kpis, _errors = recompute(spec, rows)
    return kpis
