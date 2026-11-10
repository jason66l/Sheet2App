"""Write appspec.schema.json from the Pydantic models.

Person B runs json-schema-to-typescript on the output. The same schema is the
input_schema of the LLM's forced submit_app_spec tool.

    uv run python -m scripts.export_schema
"""

import json
from pathlib import Path

from backend.spec.models import AppSpec

OUT = Path(__file__).resolve().parents[1] / "appspec.schema.json"


def main() -> None:
    schema = AppSpec.model_json_schema(mode="validation")
    OUT.write_text(json.dumps(schema, indent=2) + "\n")
    print(f"wrote {OUT} ({len(json.dumps(schema))} bytes)")


if __name__ == "__main__":
    main()
