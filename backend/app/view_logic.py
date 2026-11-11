"""Plain functions behind the saved-app routes (no database code, so they're easy to test).

TEMPORARY approval logic: counts approvals against spec.approval_rule. Julian's
core.apply_action() (weeks 9-10) replaces approval_result() when it lands.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from backend.spec.models import AppSpec


def build_rows(
    spec: AppSpec,
    records: list[dict[str, Any]],
    approver_names: dict[str, list[str]],
) -> dict[str, list[dict[str, Any]]]:
    """Records from the DB -> the rows shape the app screen uses.

    records: [{"id", "entity", "data", "state"}] in display order.
    approver_names: record id -> names of people who approved in the app.
    """
    out: dict[str, list[dict[str, Any]]] = {e.name: [] for e in spec.entities}
    for r in records:
        data = dict(r["data"] or {})
        imported = data.pop("_imported_approved_by", None) or []
        funds = data.pop("_funds", None) or []
        row = {
            **data,
            "__funds__": funds,
            "__id__": str(r["id"]),
            "__state__": r.get("state"),
            "__approved_by__": [*imported, *approver_names.get(str(r["id"]), [])],
        }
        out.setdefault(r["entity"], []).append(row)
    return out


def _amount(data: dict[str, Any], field: str) -> Decimal:
    try:
        return Decimal(str(data.get(field) or 0))
    except InvalidOperation:
        return Decimal(0)


def approvals_needed(spec: AppSpec, entity: str, data: dict[str, Any]) -> int:
    rule = spec.approval_rule
    if rule is None or rule.entity != entity:
        return 1
    return rule.required_approvals(_amount(data, rule.amount_field))


def approval_result(spec: AppSpec, entity: str, data: dict[str, Any], approvals_so_far: int) -> tuple[int, int, str]:
    """After one more approval: (given, needed, new_state)."""
    imported = len(data.get("_imported_approved_by") or [])
    given = imported + approvals_so_far + 1
    needed = approvals_needed(spec, entity, data)
    return given, needed, ("approved" if given >= needed else "submitted")


def default_user_fields(spec: AppSpec, entity: str, data: dict[str, Any], user_name: str) -> dict[str, Any]:
    """Fill person fields (e.g. "Submitted by") with the signed-in user when the form left them empty."""
    ent = spec.entity(entity)
    out = dict(data)
    if ent:
        for f in ent.fields:
            if f.type.value == "user" and not out.get(f.name):
                out[f.name] = user_name
    return out


# ------------------------------------------------------------------ permissions

CAN_APPROVE = {"admin", "approver"}
CAN_SUBMIT = {"admin", "approver", "submitter"}
CAN_INVITE = {"admin"}
CAN_MANAGE_BUDGET = {"admin"}  # add budget lines, add or correct funds


def roles_to_create(spec: AppSpec, entity: str) -> set[str]:
    """Who may add a row to this table.

    Tables with an approval workflow (expenses) take requests from every member.
    Tables without one (budget lines) define the budget itself, so only admins add to them.
    """
    ent = spec.entity(entity)
    return CAN_SUBMIT if ent is not None and ent.workflow else CAN_MANAGE_BUDGET


def budget_field(spec: AppSpec, entity: str) -> str | None:
    """The money field that holds a budget line's amount (from the app's budget table view)."""
    for v in spec.views:
        if v.type == "budget_table" and v.entity == entity:
            return v.budget_field
    return None


def duplicate_name(spec: AppSpec, entity: str, data: dict[str, Any], existing: list[dict[str, Any]]) -> str | None:
    """Expenses point at budget lines by name, so two lines can't share one."""
    ent = spec.entity(entity)
    if ent is None or ent.workflow:
        return None
    name = str(data.get(ent.display_field) or "").strip().casefold()
    if name and any(str(r.get(ent.display_field) or "").strip().casefold() == name for r in existing):
        return f"There is already a {ent.label.lower().rstrip('s')} called \"{data.get(ent.display_field)}\"."
    return None


def add_funds(data: dict[str, Any], field: str, amount: Decimal, note: str,
              by_id: str, by_name: str, at: str) -> dict[str, Any]:
    """Return the line's data with `amount` added to its budget and the change logged in _funds.

    A negative amount corrects a mistake. The budget can't go below zero.
    """
    if amount == 0:
        raise ValueError("Enter an amount other than 0.")
    if not note.strip():
        raise ValueError("Add a note saying where the money came from.")
    new_budget = _amount(data, field) + amount
    if new_budget < 0:
        raise ValueError(f"That would make this budget negative ({new_budget:.2f}).")
    entry = {"amount": str(amount.quantize(Decimal("0.01"))), "note": note.strip(), "by_id": by_id, "by": by_name, "at": at}
    return {**data, field: str(new_budget.quantize(Decimal("0.01"))), "_funds": [*(data.get("_funds") or []), entry]}


def approve_blocker(
    role: str,
    user_id: str,
    record_created_by: str | None,
    record_state: str | None,
    already_approved_by: list[str],
) -> str | None:
    """Why this user may NOT approve (or reject) this record, or None if they may."""
    if role not in CAN_APPROVE:
        return "Only approvers and admins can approve or reject requests."
    if record_state != "submitted":
        return f"This request is already {record_state or 'not submitted'}."
    if record_created_by and record_created_by == user_id:
        return "You can't approve or reject your own request."
    if user_id in already_approved_by:
        return "You already approved this request. It needs a different person."
    return None
