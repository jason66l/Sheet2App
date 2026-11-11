# Sheet2App

Turns a club's budget spreadsheet (.xlsx) into a web app: dashboard, expense form, approvals.
An LLM proposes the app as a declarative JSON spec (AppSpec); deterministic Python code does
every calculation and approval. The LLM never computes money or decides approvals.

- Plan: `docs/v1-roadmap.pdf` (12 weeks, 2 people). Background: `docs/design-doc.pdf`.
- Contract between the two halves: `docs/contract-notes.md`.

## Team
- **Julian = Person A (logic, Python):** `backend/spec/`, `backend/core/`, `tests/`, `scripts/`,
  `fixtures/`, `samples/`. Spreadsheet parsing, LLM proposal, formula engine, approval engine,
  chat edits.
- **Jason = Person B (product):** `frontend/`, FastAPI routes, Supabase (DB, auth, storage),
  deploy. Don't change B's files unless asked.

## Layout
- `backend/spec/models.py` - Pydantic AppSpec. Source of truth for the format.
- `backend/core/__init__.py` - the 4 functions B calls: run_import, compute, apply_action,
  propose_edit. Currently stubs returning fixtures. Keep their signatures stable.
- `backend/core/contracts.py` - types crossing the A/B boundary.
- `backend/core/ai/client.py` - the ONLY file that talks to the LLM (Gemini via google-genai).
- `fixtures/*.json` - hand-written AppSpecs. `samples/` - test spreadsheets + NOTES.md.

## Commands
- `uv sync` install; `uv run pytest` test; `uv run python -m scripts.export_schema` after
  any change to models.py (then tell Julian to send the schema to Jason).
- `uv run python -m scripts.check_gemini` - checks Gemini accepts the schema (sends fake data only).
- `uv run uvicorn backend.app.main:app --reload` - run the API on :8000 (needs `.env`, see `.env.example`).
- `uv run alembic upgrade head` - apply database migrations to Supabase. After changing
  `backend/app/tables.py`: `uv run alembic revision --autogenerate -m "..."`, review the file, then upgrade.
- `cd frontend && npm run dev` - run the site on :5173 (needs `frontend/.env.local`).

## Supabase (Jason)
- Supabase provides Google sign-in, Postgres and file storage. The frontend uses it only to sign in;
  all data goes through FastAPI (`backend/app/`), which checks the login token in `backend/app/auth.py`.
- Keys: publishable key (`sb_publishable_`) in `frontend/.env.local`; secret key (`sb_secret_`) and
  `DATABASE_URL` only in the root `.env`. Never commit either file.
- Every table has Row Level Security on with no policies, so the public Supabase API can't read them.
  Keep it that way for new tables.

## Rules
- Money is `Decimal`, never float. Convert at the moment a value is read.
- Python 3.12. Type hints everywhere.
- Never send real club spreadsheets to the LLM unless billing is enabled (free-tier data may be
  used by Google). Use samples with fake names.
- Every new logic function gets pytest tests. Run the full suite before saying a task is done.
- Spec format changes go through a PR Jason reviews.

## How Julian wants to work (learning mode)
Julian is a data science student who wants to learn from this project, not just finish it.
- Before writing non-trivial code, propose a short plan and wait for a go-ahead.
- Julian writes the core logic himself: the formula evaluator (`core/engine/evaluate.py`) and the
  approval engine (`core/engine/workflow.py`). For those, give hints, review his code and write
  tests, but don't write the implementation unless he asks.
- Do boilerplate, config and setup freely.
- After each change, explain what changed and why in plain language. Point out one concept worth
  learning when there is one (e.g. why Decimal, what a state machine is).
- Plain, direct language. No em-dashes.
