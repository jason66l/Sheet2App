"""Turn a ParsedWorkbook into the compact summary the LLM sees.

Kept small on purpose: headers, types, a few sample values, formula templates
and note cells. Never every row.
"""

from __future__ import annotations

import hashlib

from backend.core.contracts import SheetDigest
from backend.core.parse import ParsedWorkbook

MAX_SAMPLES = 3


def make_digest(parsed: ParsedWorkbook, file_bytes: bytes) -> SheetDigest:
    sheets = []
    for t in parsed.tables:
        sheets.append({
            "sheet": t.sheet,
            "range": t.range,
            "row_count": len(t.rows),
            "columns": [
                {
                    k: v
                    for k, v in {
                        "column": c.letter,
                        "header": c.header,
                        "type": c.type,
                        "samples": c.samples[:MAX_SAMPLES],
                        "formula": c.formula,
                        "options": c.options,
                        "dropdown_from": c.ref,
                    }.items()
                    if v not in (None, [])
                }
                for c in t.columns
            ],
        })
    return SheetDigest(
        workbook_sha256=hashlib.sha256(file_bytes).hexdigest(),
        sheets=sheets,
        notes=parsed.notes,
    )
