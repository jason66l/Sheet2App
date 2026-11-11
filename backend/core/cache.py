"""Save the AI's design per spreadsheet so retakes are instant.

Off unless PROPOSAL_CACHE=1 in .env. Keyed by the workbook's SHA-256, so a
changed file always gets a fresh AI call. Delete .cache/ to start over.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from backend.spec.models import AppSpec

log = logging.getLogger("sheet2app.cache")
ROOT = Path(__file__).resolve().parents[2]


def _dir() -> Path:
    return Path(os.getenv("PROPOSAL_CACHE_DIR", ROOT / ".cache" / "proposals"))


def enabled() -> bool:
    return os.getenv("PROPOSAL_CACHE", "0").strip() == "1"


def get(workbook_sha256: str) -> AppSpec | None:
    if not enabled():
        return None
    path = _dir() / f"{workbook_sha256}.json"
    if not path.exists():
        return None
    try:
        spec = AppSpec.model_validate_json(path.read_text())
    except Exception:  # noqa: BLE001 - a bad cache file just means a fresh AI call
        log.warning("ignoring unreadable cache file %s", path)
        return None
    log.info("loaded saved AI design from %s", path)
    return spec


def put(workbook_sha256: str, spec: AppSpec) -> None:
    if not enabled():
        return
    path = _dir()
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{workbook_sha256}.json").write_text(json.dumps(spec.model_dump(mode="json"), indent=2))
