"""Approach 2: Malloy. The model becomes a Malloy source; the report becomes one query with a nest per grouping.

Malloy has no automatic zero guard (an unguarded division yields NaN), so every division is written with nullif.
Malloy has no bound parameters at this layer: parameter values are rendered as typed literals, validated by the
request before they get here (docs: EC-L-07, EC-L-08). Anything this translator cannot express is refused by name.
"""
from __future__ import annotations

from typing import Any

from sqlglot import exp

from .. import expr
from ..errors import EngineError, UnsupportedError
from ..grid import Grid
from ..model import SemanticModel
from ..request import Binding, Report
from .base import ROW_COUNT, Backend, Plan, Statement

_OPS = {exp.EQ: "=", exp.NEQ: "!=", exp.GT: ">", exp.GTE: ">=", exp.LT: "<", exp.LTE: "<=",
        exp.Add: "+", exp.Sub: "-", exp.Mul: "*", exp.Div: "/", exp.Mod: "%"}
_TYPES = {"DATE": "date", "INT": "number", "BIGINT": "number", "DOUBLE": "number", "FLOAT": "number",
          "TEXT": "string", "VARCHAR": "string", "STRING": "string", "BOOLEAN": "boolean"}


def _unsupported(node: exp.Expression) -> UnsupportedError:
    return UnsupportedError("MALLOY_UNSUPPORTED", f"{type(node).__name__} has no Malloy translation here: {node.sql()}", construct=type(node).__name__)


def literal(value: Any, kind: str) -> str:
    if value is None:
        return "null"
    if kind == "date":
        return f"@{value}"
    if kind in ("int", "number", "INT", "DOUBLE"):
        return str(value)
    if kind == "BOOLEAN" or isinstance(value, bool):
        return "true" if value in (True, "true") else "false"
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n") + "'"


class _Translator:
    def __init__(self, values: dict[str, tuple[Any, str]] | None = None):
        self.values = values or {}          # placeholder name -> (value, kind)

    def __call__(self, node: exp.Expression) -> str:
        t = self.__call__
        if isinstance(node, exp.Paren):
            return f"({t(node.this)})"
        if isinstance(node, exp.Column):
            return f"{node.table}.{node.name}" if node.table else node.name
        if isinstance(node, exp.Literal):
            return literal(node.this, "string") if node.is_string else node.this
        if isinstance(node, exp.Boolean):
            return "true" if node.this else "false"
        if isinstance(node, exp.Null):
            return "null"
        if isinstance(node, exp.Placeholder):
            value, kind = self.values[node.name]
            return literal(value, kind)
        if isinstance(node, exp.Neg):
            return f"-{t(node.this)}"
        if type(node) in _OPS:
            return f"{t(node.this)} {_OPS[type(node)]} {t(node.expression)}"
        if isinstance(node, exp.And):
            return f"{t(node.this)} and {t(node.expression)}"
        if isinstance(node, exp.Or):
            return f"{t(node.this)} or {t(node.expression)}"
        if isinstance(node, exp.Not):
            if isinstance(node.this, exp.Is) and isinstance(node.this.expression, exp.Null):
                return f"{t(node.this.this)} is not null"
            return f"not {t(node.this)}"
        if isinstance(node, exp.Is) and isinstance(node.expression, exp.Null):
            return f"{t(node.this)} is null"
        if isinstance(node, exp.In):
            return "(" + " or ".join(f"{t(node.this)} = {t(v)}" for v in node.expressions) + ")"
        if isinstance(node, exp.Between):
            return f"({t(node.this)} >= {t(node.args['low'])} and {t(node.this)} <= {t(node.args['high'])})"
        if isinstance(node, (exp.Cast, exp.TryCast)):
            kind = _TYPES.get(node.to.this.name)
            if kind is None:
                raise _unsupported(node)
            return f"cast({t(node.this)} as {kind})"
        if isinstance(node, exp.Coalesce):
            return "coalesce(" + ", ".join(t(a) for a in [node.this, *node.expressions]) + ")"
        if isinstance(node, exp.Nullif):
            return f"nullif({t(node.this)}, {t(node.expression)})"
        if isinstance(node, (exp.Upper, exp.Lower, exp.Abs)):
            return f"{type(node).__name__.lower()}({t(node.this)})"
        if isinstance(node, (exp.Year, exp.Month, exp.Day)):
            return f"{type(node).__name__.lower()}({t(node.this.this if isinstance(node.this, exp.TsOrDsToDate) else node.this)})"
        if isinstance(node, exp.Case):
            if node.this is not None:
                raise _unsupported(node)
            return self._pick(node)
        raise _unsupported(node)

    def _pick(self, node: exp.Case) -> str:
        t = self.__call__
        branches = " ".join(f"{t(i.args['true'])} when {t(i.this)}" for i in node.args["ifs"])
        default = f" else {t(node.args['default'])}" if node.args.get("default") is not None else " else null"
        return f"pick {branches}{default}"

    def aggregate(self, tree: exp.Expression) -> str:
        t = self.__call__
        predicate = None
        if isinstance(tree, exp.Filter):
            tree, predicate = tree.this, tree.expression.this
        if isinstance(tree, exp.CountIf):
            return f"count() {{ where: {t(tree.this)} }}"
        if isinstance(tree, exp.Count):
            argument = tree.this
            if isinstance(argument, exp.Star):
                text = "count()"
            elif isinstance(argument, exp.Distinct):
                text = f"count({t(argument.expressions[0])})"        # Malloy count(x) is COUNT(DISTINCT x)
            else:                                                   # SQL COUNT(x) counts non-null values
                text = "count()"
                predicate = exp.and_(predicate, exp.Not(this=exp.Is(this=argument, expression=exp.Null()))) if predicate is not None else exp.Not(this=exp.Is(this=argument, expression=exp.Null()))
        elif isinstance(tree, (exp.Sum, exp.Avg, exp.Min, exp.Max)):
            text = f"{type(tree).__name__.lower()}({t(tree.this)})"
        else:
            raise _unsupported(tree)
        return text if predicate is None else f"{text} {{ where: {t(predicate)} }}"

    def formula(self, tree: exp.Expression) -> str:
        """Same arithmetic as the SQL backends, with the same guard on every division."""
        def visit(node):
            if isinstance(node, exp.Div):
                return f"{visit_wrapped(node.this)} / nullif({visit_wrapped(node.expression)}, 0)"
            if isinstance(node, exp.Paren):
                return f"({visit(node.this)})"
            if type(node) in _OPS:
                return f"{visit(node.this)} {_OPS[type(node)]} {visit(node.expression)}"
            return self(node)

        def visit_wrapped(node):
            return f"({visit(node)})" if isinstance(node, (exp.Add, exp.Sub, exp.Mul, exp.Div)) else visit(node)
        return visit(tree)


class Malloy(Backend):
    name = "malloy"
    engines = frozenset({"malloy-duckdb", "malloy-databricks"})

    def __init__(self, connection: str = "duckdb", table_prefix: str = ""):
        self.connection, self.table_prefix = connection, table_prefix

    def _table(self, table: str) -> str:
        return f"{self.connection}.table('{self.table_prefix}{table}')"

    def source(self, model: SemanticModel) -> str:
        t = _Translator()
        lines = [f"source: {model.name} is {self._table(model.source)} extend {{"]
        for j in model.joins:
            lines.append(f"  join_one: {j.name} is {self._table(j.table)} on {t(j.tree)}")
        lines.append("  measure:")
        lines.append(f"    {ROW_COUNT} is count()")
        lines += [f"    {m.name} is {t.aggregate(m.tree)}" for m in model.measures]
        lines += [f"    {k.name} is {t.formula(k.tree)}" for k in model.kpis]
        lines.append("}")
        return "\n".join(lines)

    def compile(self, report: Report) -> Plan:
        model = report.model
        values = {b.name: (b.value, model.params[b.name].type) for f in report.filters for b in f.bindings}
        t = _Translator(values)
        measures = [ROW_COUNT, *[m.name for m in report.atoms], *[k.name for k in report.kpis]]
        aggregate = f"aggregate: {', '.join(measures)}"

        def group(dim: str) -> str:
            d = model.dimension(dim)
            return dim if d.expr == dim else f"{dim} is {t(d.tree)}"

        conditions = [t(f.filter.tree) for f in report.filters if not f.skipped]
        for w, bindings in report.where:
            ref = t(model.dimension(w.dimension).tree)
            kinds = [("number" if b.type in ("INT", "DOUBLE") else b.type) for b in bindings]
            conditions.append("(" + " or ".join(f"{ref} = {literal(b.value, k)}" for b, k in zip(bindings, kinds)) + ")")

        lines = [self.source(model), "", f"run: {model.name} -> {{"]
        lines += [f"  where: {c}" for c in conditions]
        lines.append(f"  {aggregate}")
        nests = {}
        for scope in report.scopes:
            if not scope:
                continue
            nests[f"s{len(nests)}"] = scope
            lines.append(f"  nest: s{len(nests) - 1} is {{")
            lines.append(f"    group_by: {', '.join(group(d) for d in scope)}")
            lines.append(f"    {aggregate}")
            lines.append("  }")
        lines.append("}")
        text = "\n".join(lines)
        return Plan(self.name, report, (Statement(text, language="malloy"),), (f"{len(nests)} nests plus the top-level aggregate",))

    def assemble(self, plan: Plan, rows: list[dict[str, Any]]) -> Grid:
        report = plan.report
        grid = Grid(report.dims, tuple(m.name for m in report.atoms), tuple(k.name for k in report.kpis))
        if len(rows) != 1:
            raise EngineError("ENGINE_INCOMPLETE_RESULT", f"Malloy returns one top-level row; got {len(rows)}")
        top = rows[0]
        nests = [s for s in report.scopes if s]
        if () in report.scopes and top.get(ROW_COUNT):
            grid.add((), (), top)
        for index, scope in enumerate(nests):
            if f"s{index}" not in top:
                raise EngineError("ENGINE_INCOMPLETE_RESULT", f"the result has no nest s{index} for scope {scope}")
            for row in top[f"s{index}"]:
                if row.get(ROW_COUNT):
                    grid.add(scope, tuple(row[d] for d in scope), row)
        return grid
