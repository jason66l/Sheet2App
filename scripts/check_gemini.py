"""One-time check: does Gemini accept our AppSpec schema and return a valid spec?

Sends only the fake sample data below, never a real club's sheet.

    uv run python -m scripts.check_gemini
"""

from pydantic import ValidationError

from backend.core.ai.client import DEFAULT_MODEL, generate_json
from backend.spec.models import AppSpec

SYSTEM = (
    "You design simple web apps from spreadsheets. Return one AppSpec as JSON. "
    "Entity names are PascalCase, field names snake_case. Use the 'reimbursement' "
    "workflow with states draft, submitted, approved, rejected."
)

USER = """Workbook summary (sample data):
Sheet "Budget": columns Line (text), Budget (currency). Rows: Venue 1500, Food 1200.
  Computed column Remaining = Budget minus approved expenses for that line.
Sheet "Expenses": columns Date (date), Description (text), Budget line (matches Budget.Line),
  Submitted by (person), Amount (currency), Receipt (file link), Status (Pending/Approved/Rejected).
Note cell: "Purchases over $200 need 2 signatures."
"""


def main() -> None:
    print(f"model: {DEFAULT_MODEL}")
    data = generate_json(SYSTEM, USER, AppSpec.model_json_schema())
    try:
        spec = AppSpec.model_validate(data)
    except ValidationError as e:
        print("Gemini accepted the schema, but the answer failed validation:")
        print(e)
        return
    print("OK: Gemini accepted the schema and returned a valid AppSpec")
    print("entities:", [en.name for en in spec.entities])
    if spec.approval_rule:
        r = spec.approval_rule
        print(f"rule: {r.approvals_over} approvals over ${r.threshold}")


if __name__ == "__main__":
    main()
