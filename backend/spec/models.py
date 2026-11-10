"""AppSpec: the contract between the AI layer, the engine and the renderer.

Pydantic models are the source of truth. The JSON Schema (for the LLM's forced
tool and for Person B's TypeScript types) is generated from these classes by
scripts/export_schema.py, so the three never drift.

Design notes
- Everything is declarative. No executable code lives in a spec.
- Computed fields hold an expression string in our own small language (see
  EXPRESSIONS below). The parser/evaluator arrives in weeks 6-8; until then
  validate_expressions() only does cheap syntactic checks.
- Workflow state (draft/submitted/approved/rejected) lives on the record, not
  in a field. An imported "Status" column maps onto it.
"""

from __future__ import annotations

import re
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field as PField, model_validator

SPEC_VERSION = "1.0"

# Identifiers: snake_case for fields, PascalCase for entities.
FieldName = Annotated[str, PField(pattern=r"^[a-z][a-z0-9_]*$", max_length=64)]
EntityName = Annotated[str, PField(pattern=r"^[A-Z][A-Za-z0-9]*$", max_length=64)]

EXPRESSIONS = """
Expression language (v1)
  literals      123, 0.9, "approved"
  fields        budget                      (field on the same record)
  arithmetic    + - * /  and parentheses
  comparison    == != < <= > >=   combined with and / or / not
  functions     round(x, 2), if(cond, a, b)
  aggregates    sum(Entity.field where <cond>), count(Entity where <cond>)
                inside <cond>: bare names refer to the child record,
                `this` is the current record, `state` is the workflow state
Examples
  budget - approved - pending
  sum(Expense.amount where budget_line == this and state == "approved")
  if(budget == 0, 0, (approved + pending) / budget)
"""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- provenance


class Provenance(StrictModel):
    """Where in the workbook something came from. Shown on the review screen."""

    sheet: str
    range: str | None = PField(None, description="A1 range, e.g. 'A3:H9' or 'F4:F9'")
    confidence: float = PField(1.0, ge=0, le=1)
    note: str | None = None


# --------------------------------------------------------------------- roles


class Role(str, Enum):
    admin = "admin"
    approver = "approver"
    submitter = "submitter"


# -------------------------------------------------------------------- fields


class FieldType(str, Enum):
    text = "text"
    number = "number"
    money = "money"
    date = "date"
    enum = "enum"
    ref = "ref"
    file = "file"
    user = "user"


class Field(StrictModel):
    name: FieldName
    label: str
    type: FieldType
    required: bool = False
    options: list[str] | None = PField(None, description="enum only")
    ref_entity: EntityName | None = PField(None, description="ref only")
    min: Decimal | None = PField(None, description="number/money only")
    source: Provenance | None = None

    @model_validator(mode="after")
    def _type_specific(self) -> "Field":
        if self.type == FieldType.enum and not self.options:
            raise ValueError(f"enum field '{self.name}' needs options")
        if self.type != FieldType.enum and self.options is not None:
            raise ValueError(f"field '{self.name}': options only allowed on enum")
        if self.type == FieldType.ref and not self.ref_entity:
            raise ValueError(f"ref field '{self.name}' needs ref_entity")
        if self.type != FieldType.ref and self.ref_entity is not None:
            raise ValueError(f"field '{self.name}': ref_entity only allowed on ref")
        if self.min is not None and self.type not in (FieldType.number, FieldType.money):
            raise ValueError(f"field '{self.name}': min only allowed on number/money")
        return self


class ComputedType(str, Enum):
    number = "number"
    money = "money"
    percent = "percent"


class Computed(StrictModel):
    name: FieldName
    label: str
    type: ComputedType
    expr: str = PField(description=EXPRESSIONS)
    excel_formula: str | None = PField(
        None, description="Original column template, e.g. '=B{r}-C{r}-D{r}'"
    )
    source: Provenance | None = None


# ------------------------------------------------------------------ entities


class Entity(StrictModel):
    name: EntityName
    label: str
    fields: list[Field]
    computed: list[Computed] = []
    display_field: FieldName = PField(description="Field used as the row's name in dropdowns")
    workflow: str | None = PField(None, description="Name of a workflow in spec.workflows")
    source: Provenance | None = None

    @model_validator(mode="after")
    def _names(self) -> "Entity":
        names = [f.name for f in self.fields] + [c.name for c in self.computed]
        dupes = {n for n in names if names.count(n) > 1}
        if dupes:
            raise ValueError(f"entity '{self.name}': duplicate field names {sorted(dupes)}")
        if self.display_field not in names:
            raise ValueError(f"entity '{self.name}': display_field '{self.display_field}' not found")
        return self

    def field(self, name: str) -> Field | None:
        return next((f for f in self.fields if f.name == name), None)


# ----------------------------------------------------------------- workflows


class Transition(StrictModel):
    action: Literal["submit", "approve", "reject"]
    from_state: str
    to_state: str
    roles: list[Role]
    guard: str | None = PField(None, description="Name of a rule that must pass, e.g. 'approval_policy'")


class Workflow(StrictModel):
    name: str
    states: list[str]
    initial: str
    transitions: list[Transition]

    @model_validator(mode="after")
    def _states(self) -> "Workflow":
        if self.initial not in self.states:
            raise ValueError(f"workflow '{self.name}': initial state not in states")
        for t in self.transitions:
            for s in (t.from_state, t.to_state):
                if s not in self.states:
                    raise ValueError(f"workflow '{self.name}': unknown state '{s}'")
        return self


def reimbursement_workflow() -> Workflow:
    """The one workflow v1 ships. Fixtures and the LLM both use this shape."""
    return Workflow(
        name="reimbursement",
        states=["draft", "submitted", "approved", "rejected"],
        initial="draft",
        transitions=[
            Transition(action="submit", from_state="draft", to_state="submitted",
                       roles=[Role.submitter, Role.approver, Role.admin]),
            # 'approve' only moves to approved once the guard is satisfied;
            # until then the approval is recorded and the state stays 'submitted'.
            Transition(action="approve", from_state="submitted", to_state="approved",
                       roles=[Role.approver, Role.admin], guard="approval_policy"),
            Transition(action="reject", from_state="submitted", to_state="rejected",
                       roles=[Role.approver, Role.admin]),
        ],
    )


# --------------------------------------------------------------------- rules


class ApprovalRule(StrictModel):
    """v1's only rule type: 'N approvals over $X', no self-approval."""

    name: Literal["approval_policy"] = "approval_policy"
    entity: EntityName
    amount_field: FieldName = "amount"
    threshold: Decimal = PField(description="Strictly greater than this amount needs approvals_over")
    approvals_over: int = PField(ge=1, le=5)
    approvals_default: int = PField(1, ge=1, le=5)
    approver_roles: list[Role] = [Role.approver, Role.admin]
    exclude_submitter: Literal[True] = True
    distinct_approvers: Literal[True] = True
    source: Provenance | None = None

    def required_approvals(self, amount: Decimal) -> int:
        return self.approvals_over if amount > self.threshold else self.approvals_default


# --------------------------------------------------------------------- views


class KpiTile(StrictModel):
    label: str
    expr: str = PField(description="App-level expression, e.g. sum(BudgetLine.budget)")
    format: ComputedType = ComputedType.money


class KpiView(StrictModel):
    type: Literal["kpi"] = "kpi"
    id: str
    title: str
    tiles: list[KpiTile]


class BudgetTableView(StrictModel):
    type: Literal["budget_table"] = "budget_table"
    id: str
    title: str
    entity: EntityName
    label_field: FieldName
    budget_field: FieldName
    approved_field: FieldName
    pending_field: FieldName
    remaining_field: FieldName
    warn_at: Decimal = Decimal("0.85")


class RecordTableView(StrictModel):
    type: Literal["record_table"] = "record_table"
    id: str
    title: str
    entity: EntityName
    columns: list[FieldName]


class FormView(StrictModel):
    type: Literal["form"] = "form"
    id: str
    title: str
    entity: EntityName
    fields: list[FieldName]


class ApprovalQueueView(StrictModel):
    type: Literal["approval_queue"] = "approval_queue"
    id: str
    title: str
    entity: EntityName


View = Annotated[
    Union[KpiView, BudgetTableView, RecordTableView, FormView, ApprovalQueueView],
    PField(discriminator="type"),
]


# ------------------------------------------------------------------- AppSpec


class AppSpec(StrictModel):
    spec_version: Literal["1.0"] = SPEC_VERSION
    name: str
    description: str | None = None
    entities: list[Entity]
    workflows: list[Workflow] = []
    approval_rule: ApprovalRule | None = None
    views: list[View]

    # ---- lookups
    def entity(self, name: str) -> Entity | None:
        return next((e for e in self.entities if e.name == name), None)

    def workflow(self, name: str) -> Workflow | None:
        return next((w for w in self.workflows if w.name == name), None)

    # ---- cross-object checks. These are the "semantic" errors we send back
    # to the LLM on a retry, so messages must be specific and actionable.
    @model_validator(mode="after")
    def _cross_refs(self) -> "AppSpec":
        errors = semantic_errors(self)
        if errors:
            raise ValueError("; ".join(errors))
        return self


_AGG = re.compile(r"\b(sum|count)\(\s*([A-Z][A-Za-z0-9]*)(?:\.([a-z][a-z0-9_]*))?")


def _expr_errors(spec: AppSpec, expr: str, where: str) -> list[str]:
    """Cheap checks until the real parser lands in week 6."""
    errs: list[str] = []
    if expr.count("(") != expr.count(")"):
        errs.append(f"{where}: unbalanced parentheses in '{expr}'")
    for _, ent, fld in _AGG.findall(expr):
        e = spec.entity(ent)
        if e is None:
            errs.append(f"{where}: unknown entity '{ent}' in '{expr}'")
        elif fld and e.field(fld) is None and fld not in {c.name for c in e.computed}:
            errs.append(f"{where}: unknown field '{ent}.{fld}' in '{expr}'")
    return errs


def semantic_errors(spec: AppSpec) -> list[str]:
    errs: list[str] = []
    names = [e.name for e in spec.entities]
    if len(set(names)) != len(names):
        errs.append("duplicate entity names")
    wf_names = {w.name for w in spec.workflows}

    for e in spec.entities:
        for f in e.fields:
            if f.type == FieldType.ref and spec.entity(f.ref_entity) is None:
                errs.append(f"{e.name}.{f.name}: ref_entity '{f.ref_entity}' does not exist")
        for c in e.computed:
            errs += _expr_errors(spec, c.expr, f"{e.name}.{c.name}")
        if e.workflow and e.workflow not in wf_names:
            errs.append(f"{e.name}: workflow '{e.workflow}' does not exist")

    r = spec.approval_rule
    if r:
        e = spec.entity(r.entity)
        if e is None:
            errs.append(f"approval_rule: entity '{r.entity}' does not exist")
        else:
            af = e.field(r.amount_field)
            if af is None or af.type not in (FieldType.money, FieldType.number):
                errs.append(f"approval_rule: '{r.entity}.{r.amount_field}' must be a money/number field")
            if not e.workflow:
                errs.append(f"approval_rule: entity '{r.entity}' has no workflow")
        if r.approvals_over < r.approvals_default:
            errs.append("approval_rule: approvals_over must be >= approvals_default")

    view_ids = [v.id for v in spec.views]
    if len(set(view_ids)) != len(view_ids):
        errs.append("duplicate view ids")
    for v in spec.views:
        if isinstance(v, KpiView):
            for t in v.tiles:
                errs += _expr_errors(spec, t.expr, f"view '{v.id}' tile '{t.label}'")
            continue
        e = spec.entity(v.entity)
        if e is None:
            errs.append(f"view '{v.id}': entity '{v.entity}' does not exist")
            continue
        known = {f.name for f in e.fields} | {c.name for c in e.computed}
        refs: list[str] = []
        if isinstance(v, BudgetTableView):
            refs = [v.label_field, v.budget_field, v.approved_field, v.pending_field, v.remaining_field]
        elif isinstance(v, RecordTableView):
            refs = v.columns
        elif isinstance(v, FormView):
            refs = v.fields
            computed_in_form = set(v.fields) & {c.name for c in e.computed}
            if computed_in_form:
                errs.append(f"view '{v.id}': computed fields can't be form inputs: {sorted(computed_in_form)}")
        for name in refs:
            if name not in known:
                errs.append(f"view '{v.id}': unknown field '{e.name}.{name}'")
    return errs
