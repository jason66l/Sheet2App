"""Demo server: upload a spreadsheet, get the generated app back. No sign-in, no Supabase.

Run from the repo root:
    uv run uvicorn backend.demo_server:app --reload --port 8000

The full product (sign-in, saving, invites) is backend/app/main.py. This file
only exists to show spreadsheet -> AI -> app without that setup.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.core import cache, run_import
from backend.core.ai.client import DEFAULT_MODEL
from backend.core.demo_values import display_rows, kpi_values
from backend.core.parse import parse_workbook

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
MAX_BYTES = 25 * 1024 * 1024

app = FastAPI(title="Sheet2App demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/demo/import")
def demo_import(file: UploadFile) -> dict:
    # A plain `def` route runs in a worker thread, so the slow AI call doesn't block the server.
    name = file.filename or "upload.xlsx"
    if not name.lower().endswith(".xlsx"):
        raise HTTPException(400, "Please upload an Excel .xlsx file")
    data = file.file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is over 25 MB")

    start = time.monotonic()
    from_cache = cache.get(hashlib.sha256(data).hexdigest()) is not None
    try:
        result = run_import(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    rows = display_rows(result.proposal, parse_workbook(data))
    ai_failed = any(w.startswith("AI step failed") for w in result.warnings)
    return {
        "file_name": name,
        "seconds": round(time.monotonic() - start, 1),
        "source": "fallback" if ai_failed else ("cache" if from_cache else "ai"),
        "model": DEFAULT_MODEL,
        "spec": result.proposal.model_dump(mode="json"),
        "rows": rows,
        "kpis": kpi_values(result.proposal, rows),
        "warnings": result.warnings,
    }
