"""The formula engine: turns the spec's expression strings into numbers.

Two steps, like most small languages:
1. parse(text) reads the expression once and builds a tree of nodes (an AST).
   "budget - approved - pending" becomes Sub(Sub(Name budget, Name approved), Name pending).
2. Evaluator walks that tree against the current rows and returns a value.

The language is described in backend/spec/models.py (EXPRESSIONS):
  literals 123, 0.9, "approved"; field names; + - * / and parentheses;
  == != < <= > >= with and / or / not; round(x, n), if(c, a, b), abs(x), min(...), max(...);
  sum(Entity.field where <cond>), count(Entity where <cond>), avg(...)
  Inside <cond>, bare names are the child record's fields, `state` is its workflow
  state and `this` is the record being computed (its display name, or this.field).

All numbers are Decimal, never float: 0.1 + 0.2 must be exactly 0.3 when it is money.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any

from backend.spec.models import AppSpec, Entity


class ExprError(ValueError):
    """The expression can't be parsed, or can't be evaluated on this data."""


# ------------------------------------------------------------------ tokens

_TOKEN = re.compile(
    r"""\s*(?:
        (?P<num>\d+(?:\.\d+)?|\.\d+)
      | (?P<str>"[^"]*"|'[^']*')
      | (?P<op>==|!=|<=|>=|[-+*/(),.<>])
      | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
    )""",
    re.X,
)
_KEYWORDS = {"and", "or", "not", "where", "true", "false"}
_AGGREGATES = {"sum", "count", "avg"}


@dataclass(frozen=True)
class Tok:
    kind: str  # num, str, op, name, kw, end
    text: str


def _tokenize(text: str) -> list[Tok]:
    toks, pos = [], 0
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise ExprError(f"Unexpected character {text[pos]!r} in {text!r}")
        kind = m.lastgroup or ""
        val = m.group(kind)
        if kind == "name" and val.lower() in _KEYWORDS:
            kind, val = "kw", val.lower()
        toks.append(Tok(kind, val))
        pos = m.end()
    toks.append(Tok("end", ""))
    return toks


# ------------------------------------------------------------------ AST nodes


@dataclass(frozen=True)
class Num:
    value: Decimal


@dataclass(frozen=True)
class Str:
    value: str


@dataclass(frozen=True)
class Bool:
    value: bool


@dataclass(frozen=True)
class Name:
    name: str  # field name, "state" or "this"


@dataclass(frozen=True)
class ThisField:
    name: str  # this.field


@dataclass(frozen=True)
class Unary:
    op: str  # "-" or "not"
    arg: Any


@dataclass(frozen=True)
class Binary:
    op: str
    left: Any
    right: Any


@dataclass(frozen=True)
class Call:
    fn: str
    args: tuple[Any, ...]


@dataclass(frozen=True)
class Aggregate:
    fn: str  # sum, count, avg
    entity: str
    field: str | None
    where: Any | None


# ------------------------------------------------------------------ parser


class _Parser:
    """Recursive descent: one method per precedence level, lowest first."""

    def __init__(self, text: str):
        self.text = text
        self.toks = _tokenize(text)
        self.i = 0

    def peek(self) -> Tok:
        return self.toks[self.i]

    def next(self) -> Tok:
        t = self.toks[self.i]
        self.i += 1
        return t

    def accept(self, kind: str, text: str | None = None) -> Tok | None:
        t = self.peek()
        if t.kind == kind and (text is None or t.text == text):
            self.i += 1
            return t
        return None

    def expect(self, kind: str, text: str | None = None) -> Tok:
        t = self.accept(kind, text)
        if t is None:
            got = self.peek().text or "end of expression"
            raise ExprError(f"Expected {text or kind} but found {got!r} in {self.text!r}")
        return t

    def parse(self) -> Any:
        node = self.or_()
        self.expect("end")
        return node

    def or_(self) -> Any:
        node = self.and_()
        while self.accept("kw", "or"):
            node = Binary("or", node, self.and_())
        return node

    def and_(self) -> Any:
        node = self.not_()
        while self.accept("kw", "and"):
            node = Binary("and", node, self.not_())
        return node

    def not_(self) -> Any:
        if self.accept("kw", "not"):
            return Unary("not", self.not_())
        return self.compare()

    def compare(self) -> Any:
        node = self.add()
        t = self.peek()
        if t.kind == "op" and t.text in {"==", "!=", "<", "<=", ">", ">="}:
            self.next()
            node = Binary(t.text, node, self.add())
        return node

    def add(self) -> Any:
        node = self.mul()
        while (t := self.peek()).kind == "op" and t.text in "+-":
            self.next()
            node = Binary(t.text, node, self.mul())
        return node

    def mul(self) -> Any:
        node = self.unary()
        while (t := self.peek()).kind == "op" and t.text in "*/":
            self.next()
            node = Binary(t.text, node, self.unary())
        return node

    def unary(self) -> Any:
        if self.accept("op", "-"):
            return Unary("-", self.unary())
        if self.accept("op", "+"):
            return self.unary()
        return self.primary()

    def primary(self) -> Any:
        t = self.next()
        if t.kind == "num":
            return Num(Decimal(t.text))
        if t.kind == "str":
            return Str(t.text[1:-1])
        if t.kind == "kw" and t.text in ("true", "false"):
            return Bool(t.text == "true")
        if t.kind == "op" and t.text == "(":
            node = self.or_()
            self.expect("op", ")")
            return node
        if t.kind == "name":
            fn = t.text.lower()
            if self.accept("op", "("):
                if fn in _AGGREGATES and self._entity_next():
                    return self.aggregate(fn)
                args = [] if self.accept("op", ")") else self.args()
                return Call(fn, tuple(args))
            if t.text == "this" and self.accept("op", "."):
                return ThisField(self.expect("name").text)
            if self.peek().kind == "op" and self.peek().text == ".":
                raise ExprError(f"{t.text}.{self.toks[self.i + 1].text} only works inside sum()/count()")
            return Name(t.text)
        raise ExprError(f"Unexpected {t.text or 'end of expression'!r} in {self.text!r}")

    def _entity_next(self) -> bool:
        t = self.peek()
        return t.kind == "name" and t.text[:1].isupper()

    def args(self) -> list[Any]:
        out = [self.or_()]
        while self.accept("op", ","):
            out.append(self.or_())
        self.expect("op", ")")
        return out

    def aggregate(self, fn: str) -> Aggregate:
        entity = self.expect("name").text
        field = self.expect("name").text if self.accept("op", ".") else None
        if fn != "count" and field is None:
            raise ExprError(f"{fn}({entity}) needs a field, e.g. {fn}({entity}.amount)")
        where = self.or_() if self.accept("kw", "where") else None
        self.expect("op", ")")
        return Aggregate(fn, entity, field, where)


@lru_cache(maxsize=1024)
def parse(text: str) -> Any:
    """Expression string -> AST. Cached: each spec has only a handful of expressions."""
    return _Parser(text).parse()


# ------------------------------------------------------------------ values


def to_decimal(v: Any) -> Decimal | None:
    """Turn a stored value into a Decimal. '$1,200.50' and 1200.5 both work; blank is None."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, int):
        return Decimal(v)
    if isinstance(v, float):
        return Decimal(str(v))  # str() first, so 0.1 stays 0.1 and not 0.1000000000000000055...
    s = str(v).strip().replace(",", "").replace("$", "")
    if not s:
        return None
    if s.endswith("%"):
        d = to_decimal(s[:-1])
        return None if d is None else d / 100
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _num(v: Any) -> Decimal:
    """For arithmetic: blank counts as 0 (an empty cell in Excel does too)."""
    if isinstance(v, str) and v.strip() and to_decimal(v) is None:
        raise ExprError(f"{v!r} is not a number")
    d = to_decimal(v)
    return Decimal(0) if d is None else d


def _same(a: Any, b: Any) -> bool:
    """Equality that matches how people type: numbers by value, text ignoring case and spaces."""
    da, db = to_decimal(a), to_decimal(b)
    if da is not None and db is not None:
        return da == db
    norm = lambda x: "" if x is None else str(x).strip().casefold()  # noqa: E731
    return norm(a) == norm(b)


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    d = to_decimal(v)
    if d is not None:
        return d != 0
    return bool(v)


# ------------------------------------------------------------------ evaluation

Row = dict[str, Any]


class Evaluator:
    """Computes every computed field and KPI tile for one app's rows.

    rows: {"BudgetLine": [{"line": "Venue", "budget": "1500", "__state__": None}, ...], ...}
    Computed fields may use other computed fields (remaining uses approved), on the same
    record or through sum(). Each value is computed once and remembered; a formula that
    ends up depending on itself raises ExprError instead of looping forever.
    """

    def __init__(self, spec: AppSpec, rows: dict[str, list[Row]]):
        self.spec = spec
        self.rows = rows
        self._memo: dict[tuple[int, str], Any] = {}
        self._busy: set[tuple[int, str]] = set()
        self._entity_of: dict[int, Entity] = {}
        for ent in spec.entities:
            for r in rows.get(ent.name, []):
                self._entity_of[id(r)] = ent

    # A record's value for a name: a computed field (evaluated) or a stored field.
    def value(self, row: Row, name: str) -> Any:
        if name == "state":
            return row.get("__state__")
        ent = self._entity_of.get(id(row))
        comp = next((c for c in ent.computed if c.name == name), None) if ent else None
        if comp is None:
            if ent is not None and name not in row and ent.field(name) is None:
                raise ExprError(f"{ent.name} has no field '{name}'")
            return row.get(name)
        key = (id(row), name)
        if key in self._memo:
            return self._memo[key]
        if key in self._busy:
            raise ExprError(f"{ent.name}.{name} depends on itself")
        self._busy.add(key)
        try:
            result = self.eval(parse(comp.expr), row=row, parent=None)
        finally:
            self._busy.discard(key)
        self._memo[key] = result
        return result

    def eval(self, node: Any, row: Row | None, parent: Row | None) -> Any:
        """row: the record names refer to. parent: the record `this` refers to (inside where)."""
        match node:
            case Num(value=v) | Str(value=v) | Bool(value=v):
                return v
            case Name(name="this"):
                target = parent if parent is not None else row
                if target is None:
                    raise ExprError("`this` has no record here")
                ent = self._entity_of.get(id(target))
                return target.get(ent.display_field) if ent else None
            case ThisField(name=n):
                target = parent if parent is not None else row
                if target is None:
                    raise ExprError("`this` has no record here")
                return self.value(target, n)
            case Name(name=n):
                if row is None:
                    raise ExprError(f"'{n}' needs a record; use sum() or count() at app level")
                return self.value(row, n)
            case Unary(op="-", arg=a):
                return -_num(self.eval(a, row, parent))
            case Unary(op="not", arg=a):
                return not _truthy(self.eval(a, row, parent))
            case Binary(op="and", left=l, right=r):
                return _truthy(self.eval(l, row, parent)) and _truthy(self.eval(r, row, parent))
            case Binary(op="or", left=l, right=r):
                return _truthy(self.eval(l, row, parent)) or _truthy(self.eval(r, row, parent))
            case Binary(op=op, left=l, right=r):
                return self._binary(op, self.eval(l, row, parent), self.eval(r, row, parent))
            case Call(fn=fn, args=args):
                return self._call(fn, args, row, parent)
            case Aggregate():
                return self._aggregate(node, row)
        raise ExprError(f"Can't evaluate {node!r}")

    def _binary(self, op: str, a: Any, b: Any) -> Any:
        if op == "==":
            return _same(a, b)
        if op == "!=":
            return not _same(a, b)
        if op in ("<", "<=", ">", ">="):
            x, y = _num(a), _num(b)
            return {"<": x < y, "<=": x <= y, ">": x > y, ">=": x >= y}[op]
        x, y = _num(a), _num(b)
        if op == "+":
            return x + y
        if op == "-":
            return x - y
        if op == "*":
            return x * y
        if op == "/":
            if y == 0:
                raise ExprError("Division by zero")
            return x / y
        raise ExprError(f"Unknown operator {op}")

    def _call(self, fn: str, args: tuple[Any, ...], row: Row | None, parent: Row | None) -> Any:
        if fn == "if":
            if len(args) != 3:
                raise ExprError("if() takes 3 arguments: if(condition, then, else)")
            # Only the chosen branch runs, so if(budget == 0, 0, x / budget) never divides by zero.
            branch = args[1] if _truthy(self.eval(args[0], row, parent)) else args[2]
            return self.eval(branch, row, parent)
        vals = [self.eval(a, row, parent) for a in args]
        if fn == "round":
            places = int(_num(vals[1])) if len(vals) > 1 else 0
            return _num(vals[0]).quantize(Decimal(1).scaleb(-places))
        if fn == "abs" and len(vals) == 1:
            return abs(_num(vals[0]))
        if fn in ("min", "max") and vals:
            nums = [_num(v) for v in vals]
            return min(nums) if fn == "min" else max(nums)
        raise ExprError(f"Unknown function {fn}()")

    def _aggregate(self, node: Aggregate, row: Row | None) -> Decimal:
        ent = self.spec.entity(node.entity)
        if ent is None:
            raise ExprError(f"Unknown table {node.entity}")
        children = self.rows.get(node.entity, [])
        if node.where is not None:
            # Inside where: names are the child's fields, `this` is the record we're computing.
            children = [c for c in children if _truthy(self.eval(node.where, c, row))]
        if node.fn == "count":
            return Decimal(len(children))
        assert node.field is not None
        values = [_num(self.value(c, node.field)) for c in children]
        if node.fn == "avg":
            return sum(values, Decimal(0)) / len(values) if values else Decimal(0)
        return sum(values, Decimal(0))


# ------------------------------------------------------------------ public helpers


def _out(v: Any, kind: str) -> str | None:
    """Decimal -> string for JSON. Money to the cent; others trimmed of trailing zeros."""
    if isinstance(v, bool):
        return "1" if v else "0"
    d = to_decimal(v)
    if d is None:
        return None
    if kind == "money":
        return str(d.quantize(Decimal("0.01")))
    d = d.quantize(Decimal("0.000001")).normalize()
    return format(d, "f")


def check(expr: str) -> str | None:
    """Return an error message if the expression can't be parsed, else None."""
    try:
        parse(expr)
        return None
    except ExprError as exc:
        return str(exc)


def recompute(spec: AppSpec, rows: dict[str, list[Row]]) -> tuple[dict[str, str | None], list[str]]:
    """Fill every computed field on every row (in place) and evaluate every KPI tile.

    Returns ({"view_id/tile label": value}, [error messages]). A formula that fails leaves
    the row's old value (e.g. the one Excel saved) and is reported once in the errors.
    """
    ev = Evaluator(spec, rows)
    errors: list[str] = []
    seen: set[str] = set()

    def note(where: str, exc: Exception) -> None:
        msg = f"{where}: {exc}"
        if where not in seen:
            seen.add(where)
            errors.append(msg)

    for ent in spec.entities:
        for row in rows.get(ent.name, []):
            for comp in ent.computed:
                try:
                    row[comp.name] = _out(ev.value(row, comp.name), comp.type.value)
                except ExprError as exc:
                    note(f"{ent.name}.{comp.name}", exc)

    kpis: dict[str, str | None] = {}
    for view in spec.views:
        if view.type != "kpi":
            continue
        for tile in view.tiles:
            key = f"{view.id}/{tile.label}"
            try:
                kpis[key] = _out(ev.eval(parse(tile.expr), row=None, parent=None), tile.format.value)
            except ExprError as exc:
                kpis[key] = None
                note(f"tile '{tile.label}'", exc)
    return kpis, errors
