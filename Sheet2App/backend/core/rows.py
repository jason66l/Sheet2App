"""Map spreadsheet rows onto the entities the AI proposed (ImportResult.rows).

Each row becomes {field_name: value}. Two special keys, per contract-notes item 4:
- "__state__": workflow state from the Status column (Approved -> approved, Pending -> submitted, ...)
- "__approved_by__": list of names from the "Approved by" column
B's /confirm route turns those into record.state and approval rows.
"""

from __future__ import annotations

import re
from typing import Any

from backend.core.parse import ParsedWorkbook, Table
from backend.spec.models import AppSpec, Entity

STATUS_TO_STATE = {"approved": "approved", "pending": "submitted", "submitted": "submitted",
                   "rejected": "rejected", "draft": "draft"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _column_letter(source_range: str | None) -> str | None:
    m = re.match(r"\$?([A-Z]{1,3})", source_range or "")
    return m.group(1) if m else None


def _header_for(field_name: str, label: str, source_range: str | None, table: Table) -> str | None:
    letter = _column_letter(source_range)
    for col in table.columns:
        if letter and col.letter == letter:
            return col.header
    for col in table.columns:
        if _norm(col.header) in (_norm(label), _norm(field_name)):
            return col.header
    return None


def _table_for(entity: Entity, parsed: ParsedWorkbook) -> Table | None:
    if entity.source:
        for t in parsed.tables:
            if t.sheet == entity.source.sheet:
                return t
    return None


def rows_for_entities(spec: AppSpec, parsed: ParsedWorkbook) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for entity in spec.entities:
        table = _table_for(entity, parsed)
        if table is None:
            continue
        mapping = {
            f.name: _header_for(f.name, f.label, f.source.range if f.source else None, table)
            for f in entity.fields
        }
        status_col = next((c.header for c in table.columns if _norm(c.header) == "status"), None)
        approved_by_col = next((c.header for c in table.columns if _norm(c.header) == "approvedby"), None)

        rows = []
        for raw in table.rows:
            row: dict[str, Any] = {name: raw.get(header) for name, header in mapping.items() if header}
            if entity.workflow and status_col:
                status = str(raw.get(status_col) or "").strip().lower()
                row["__state__"] = STATUS_TO_STATE.get(status, "draft")
            if entity.workflow and approved_by_col and raw.get(approved_by_col):
                row["__approved_by__"] = [n.strip() for n in str(raw[approved_by_col]).split(",") if n.strip()]
            rows.append(row)
        out[entity.name] = rows
    return out
