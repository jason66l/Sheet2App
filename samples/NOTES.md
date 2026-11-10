# Sample spreadsheets

One entry per sample: what the right app is. Target: 10 real club sheets by end of week 1.

| File | Source | Right app | Gotchas |
|---|---|---|---|
| Event_Budget_2026.xlsx | Rebuilt from design mockups (scripts/make_event_budget_sample.py); Members sheet is placeholder | fixtures/event_budget.json | Rule lives in a note cell (Budget!A12) and names specific roles (president + treasurer); "Approved by" is a comma list of names to split into approvals; Pending row 11 already has 1 of 2 approvals; row 6 receipt is a quote, not a receipt; cached values are floats (742.4) so compare as Decimal with $0.005 tolerance |
