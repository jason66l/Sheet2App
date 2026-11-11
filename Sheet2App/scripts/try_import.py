"""Run the real import pipeline on a spreadsheet and print what the AI proposed.

Calls Gemini, so only use sample files with fake names on the free tier.

    uv run python -m scripts.try_import samples/Event_Budget_2026.xlsx
    uv run python -m scripts.try_import samples/Event_Budget_2026.xlsx --json   # full AppSpec
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

from backend.core import run_import


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    path = Path(sys.argv[1])
    start = time.monotonic()
    result = run_import(path.read_bytes())
    spec = result.proposal

    if "--json" in sys.argv:
        print(json.dumps(spec.model_dump(mode="json"), indent=2))
        return

    print(f"\n{spec.name}  ({time.monotonic() - start:.1f}s)")
    print(f"  {spec.description or ''}")
    for e in spec.entities:
        print(f"\n  {e.name}: {len(result.rows.get(e.name, []))} rows")
        for f in e.fields:
            print(f"    {f.name:<18} {f.type.value}")
        for c in e.computed:
            print(f"    {c.name:<18} = {c.expr}")
    if spec.approval_rule:
        r = spec.approval_rule
        print(f"\n  Rule: {r.approvals_over} approvals over ${r.threshold} on {r.entity}.{r.amount_field}")
    print(f"\n  Views: {', '.join(v.type for v in spec.views)}")
    for w in result.warnings:
        print(f"  ! {w}")


if __name__ == "__main__":
    main()
