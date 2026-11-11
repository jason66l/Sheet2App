"""Read an .xlsx into plain Python: tables, column types, formulas and note cells.

No LLM here. This is the deterministic first pass; its output (ParsedWorkbook)
feeds digest.py, which is what the LLM sees.

Heuristics (good enough for v1 sheets with one table per sheet):
- Header row: the first row with 2+ text cells whose next row has data.
- Table ends at the first fully blank row, or a row whose first cell says "Total".
- Text cells outside the table are "notes" (titles, rules like "over $200 needs 2 signatures").
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import openpyxl
from openpyxl.cell.cell import Cell
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

TOTAL_WORDS = {"total", "totals", "grand total", "sum"}
MAX_ENUM_OPTIONS = 12


@dataclass
class Column:
    letter: str
    header: str
    type: str                     # text | number | money | percent | date | enum | ref
    samples: list[Any] = field(default_factory=list)
    formula: str | None = None    # template with row numbers as {r}, e.g. "=B{r}-C{r}-D{r}"
    options: list[str] | None = None    # enum choices
    ref: str | None = None              # "Sheet!A4:A9" when a dropdown points at another range


@dataclass
class Table:
    sheet: str
    header_row: int
    first_row: int
    last_row: int
    columns: list[Column]
    rows: list[dict[str, Any]]    # header -> JSON-safe value (Decimal as str, dates ISO)

    @property
    def range(self) -> str:
        return f"{self.columns[0].letter}{self.header_row}:{self.columns[-1].letter}{self.last_row}"


@dataclass
class ParsedWorkbook:
    tables: list[Table]
    notes: list[dict[str, str]]   # {"sheet", "cell", "text"}
    formula_cells: int


# ---------------------------------------------------------------- helpers


def _is_text(v: Any) -> bool:
    return isinstance(v, str) and v.strip() != "" and not v.startswith("=")


def _json_safe(v: Any) -> Any:
    """Money must never become a float: numbers go through Decimal(str(x))."""
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        return str(Decimal(str(v)))
    if isinstance(v, datetime):
        return v.date().isoformat() if v.time() == datetime.min.time() else v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return str(v).strip()


def _template(formula: str, row: int) -> str:
    """'=B6-C6-D6' at row 6 -> '=B{r}-C{r}-D{r}'. Absolute refs like $A$4 stay as they are."""
    # Matches A6 and $A6 (row-relative) but not A$6 or $A$6 (row-absolute).
    return re.sub(rf"(?<![A-Za-z0-9$])(\$?[A-Z]{{1,3}}){row}(?!\d)", r"\1{r}", formula)


def _validations(ws: Worksheet) -> dict[str, str]:
    """Column letter -> list formula, e.g. {'G': '"Pending,Approved,Rejected"', 'C': 'Budget!$A$4:$A$9'}."""
    out: dict[str, str] = {}
    for dv in ws.data_validations.dataValidation:
        if dv.type != "list" or not dv.formula1:
            continue
        for rng in str(dv.sqref).split():
            letter = re.match(r"[A-Z]+", rng)
            if letter:
                out[letter.group(0)] = dv.formula1
    return out


def _column_type(cells: list[Cell], values: list[Any]) -> str:
    fmt = next((c.number_format for c in cells if c.value is not None), "General")
    present = [v for v in values if v is not None and v != ""]
    if not present:
        return "text"
    if all(isinstance(v, (datetime, date)) for v in present):
        return "date"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in present):
        if "%" in fmt:
            return "percent"
        if "$" in fmt or "€" in fmt or "£" in fmt or "[$" in fmt:
            return "money"
        return "number"
    return "text"


def _find_header(ws: Worksheet) -> int | None:
    for r in range(1, min(ws.max_row, 30) + 1):
        texts = [c.value for c in ws[r] if _is_text(c.value)]
        nxt = [c.value for c in ws[r + 1]] if r < ws.max_row else []
        if len(texts) >= 2 and any(v is not None for v in nxt):
            return r
    return None


# ---------------------------------------------------------------- main


def parse_workbook(file_bytes: bytes) -> ParsedWorkbook:
    formulas_wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=False)
    values_wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)

    tables: list[Table] = []
    notes: list[dict[str, str]] = []
    formula_cells = 0

    for ws in formulas_wb.worksheets:
        vs = values_wb[ws.title]
        formula_cells += sum(
            1 for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=")
        )
        header = _find_header(ws)
        in_table: set[tuple[int, int]] = set()

        if header is not None:
            head_cells = [c for c in ws[header] if _is_text(c.value)]
            cols_idx = [c.column for c in head_cells]

            last = header
            for r in range(header + 1, ws.max_row + 1):
                row_vals = [ws.cell(r, ci).value for ci in cols_idx]
                if all(v is None or v == "" for v in row_vals):
                    break
                first = row_vals[0]
                if isinstance(first, str) and first.strip().lower() in TOTAL_WORDS:
                    break
                last = r

            if last > header:
                validations = _validations(ws)
                columns: list[Column] = []
                for hc in head_cells:
                    letter = get_column_letter(hc.column)
                    cells = [ws.cell(r, hc.column) for r in range(header + 1, last + 1)]
                    values = [vs.cell(r, hc.column).value for r in range(header + 1, last + 1)]
                    col = Column(letter=letter, header=str(hc.value).strip(), type=_column_type(cells, values))

                    first_formula = next(
                        (c for c in cells if isinstance(c.value, str) and c.value.startswith("=")), None
                    )
                    if first_formula is not None:
                        col.formula = _template(first_formula.value, first_formula.row)

                    rule = validations.get(letter)
                    if rule and rule.startswith('"'):
                        col.type, col.options = "enum", [o.strip() for o in rule.strip('"').split(",")]
                    elif rule:
                        col.type, col.ref = "ref", rule.replace("$", "")
                    elif col.type == "text" and col.formula is None:
                        distinct = {v for v in values if isinstance(v, str)}
                        if 1 < len(distinct) <= MAX_ENUM_OPTIONS and len(distinct) <= len(values) / 3:
                            col.type, col.options = "enum", sorted(distinct)

                    col.samples = [_json_safe(v) for v in values if v is not None][:5]
                    columns.append(col)

                rows = []
                for r in range(header + 1, last + 1):
                    rows.append({col.header: _json_safe(vs[f"{col.letter}{r}"].value) for col in columns})
                    for ci in cols_idx:
                        in_table.add((r, ci))
                for ci in cols_idx:
                    in_table.add((header, ci))

                tables.append(Table(ws.title, header, header + 1, last, columns, rows))

        for row in ws.iter_rows():
            for c in row:
                text = c.value.strip() if isinstance(c.value, str) else ""
                if _is_text(c.value) and (c.row, c.column) not in in_table and text.lower() not in TOTAL_WORDS:
                    notes.append({"sheet": ws.title, "cell": c.coordinate, "text": text})

    return ParsedWorkbook(tables=tables, notes=notes, formula_cells=formula_cells)
