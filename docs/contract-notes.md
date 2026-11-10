# Contract notes: Person A to Person B (week 1)

The AppSpec format lives in `backend/spec/models.py`. `appspec.schema.json` is generated from it
(`uv run python -m scripts.export_schema`). Generate `frontend/src/types/appspec.ts` from that file.
Please don't edit the JSON by hand; change the models instead (via a PR we both review).

Until the real logic lands, the four functions in `backend/core/__init__.py` return the fixtures in
`fixtures/`, so every route and screen can be built now.

## Changes to the roadmap's signatures (please confirm)

1. **`apply_action` needs the approvals already given.** `Record` now has an `approvals` list.
   Load it from the approvals table before calling, and save any new approval it returns.
2. **`compute()` returns dashboard totals too.** It returns
   `ComputeResult(per_record={record_id: {field: value}}, app={tile_label: value})`
   instead of only the per-record dict.
3. **`run_import()` returns the spreadsheet rows.** `ImportResult.rows` holds them, keyed by
   entity name, so `/imports/{id}/confirm` can insert records without reading the file again.
4. **Status and "Approved by" are special.** The Status column becomes the record's workflow
   `state`, not a field. "Approved by" (e.g. "Kai Patel, Priya Shah") becomes approval rows.
   Person A matches those names to members at import; B creates the users and memberships.

## Other decisions

- LLM provider is Gemini (Google AI Studio), not Anthropic. Env var is `GEMINI_API_KEY`
  (see `.env.example`). Only fake or sample data goes to the free tier; turn on billing before
  real club sheets are used, since free-tier data can be used by Google.
- Python is pinned to 3.12 (`.python-version`).
- Money is `Decimal` in Python and a numeric string in JSON. Never float.
