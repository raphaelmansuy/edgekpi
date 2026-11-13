"""Front-end: infer a SemanticModel from the registry's templated SQL.

A legacy template is `SELECT {{ group_by_list }}, <one aggregate expression> AS kpi_value FROM <fact> [LEFT JOIN ...]
WHERE ... GROUP BY {{ group_by_list }}`. The inference reads it as relational algebra (sqlglot), keeps what it can
prove, and refuses the rest with a reason. Nothing here executes the template; parity.py does that (docs: 08).

Rewriting happens INSIDE the aggregation: lifting a row filter into FILTER, naming the aggregates, guarding the
division. A rewrite on top of an aggregated result would not work because aggregation loses the rows.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Mapping

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from . import expr
from .backends.base import Engine
from .errors import DefinitionError, GrainError, KpiError
from .grain import check_joins
from .model import Dimension, Filter, Join, Kpi, Measure, Param, SemanticModel

SLOT, SENTINEL = "{{ group_by_list }}", "__group_by_list__"
_BLOCK = re.compile(r"-- kpi: (\S+) \| (\w+)\n(.*?;)", re.S)
_PARAM_TYPES = {"DATE": "date", "INT": "int", "BIGINT": "int", "DOUBLE": "number", "FLOAT": "number", "DECIMAL": "number"}


@dataclass(frozen=True)
class Template:
    kpi_id: str
    alias: str             # becomes the KPI name
    sql: str


@dataclass
class Inference:
    model: SemanticModel
    accepted: dict[str, str] = field(default_factory=dict)      # kpi_id -> KPI name
    refused: dict[str, str] = field(default_factory=dict)       # kpi_id -> "CODE: reason"
    grain: dict[str, int] | None = None
    notes: list[str] = field(default_factory=list)


def parse_templates(text: str) -> list[Template]:
    return [Template(k, a, body.strip().rstrip(";")) for k, a, body in _BLOCK.findall(text)]


def _dbx(node: exp.Expression) -> str:
    return node.sql(dialect=expr.DIALECT)


def _conjuncts(node):
    if node is None:
        return []
    if isinstance(node, exp.And):
        return _conjuncts(node.this) + _conjuncts(node.expression)
    return [] if node.sql() == "1 = 1" else [node]


class _Refusal(KpiError):
    pass


def _refuse(code: str, message: str):
    raise _Refusal(code, message)


def _canonical_columns(tree: exp.Expression, fact_alias: str, joins: Mapping[str, str]) -> exp.Expression:
    def visit(node):
        if isinstance(node, exp.Column):
            if node.table == fact_alias:
                return exp.column(node.name)
            if node.table in joins:
                return exp.column(node.name, table=joins[node.table])
            if not node.table and joins:
                _refuse("INFER_UNQUALIFIED_COLUMN", f"column {node.name} is unqualified in a query with joins")
            if node.table:
                _refuse("INFER_UNKNOWN_ALIAS", f"alias {node.table} is not in the FROM clause")
        return node
    return tree.transform(visit)


def _one_spelling(tree: exp.Expression) -> exp.Expression:
    """COUNT_IF(p), SUM(CASE WHEN p THEN 1 ELSE 0 END) and COUNT(*) FILTER (WHERE p) count the same rows."""
    def visit(node):
        predicate = None
        if isinstance(node, exp.CountIf):
            predicate = node.this
        elif isinstance(node, exp.Sum) and isinstance(node.this, exp.Case) and not node.this.this:
            ifs, default = node.this.args.get("ifs") or [], node.this.args.get("default")
            if len(ifs) == 1 and ifs[0].args["true"].sql() == "1" and default is not None and default.sql() == "0":
                predicate = ifs[0].this
        if predicate is None:
            return node
        return exp.Filter(this=exp.Count(this=exp.Star()), expression=exp.Where(this=predicate.copy()))
    return tree.transform(visit)


def _guarded_division(tree: exp.Expression) -> tuple[exp.Expression, bool]:
    """try_divide(a, b), a * 1.0 / NULLIF(b, 0) and a / NULLIF(b, 0) become Div(a, b), which the library guards."""
    changed = [False]

    def strip_one(node):
        if isinstance(node, exp.Mul) and node.expression.sql() == "1.0":
            return node.this
        return node

    def visit(node):
        if isinstance(node, exp.SafeDivide):
            changed[0] = True
            return exp.Div(this=node.this, expression=node.expression)
        if isinstance(node, exp.Div) and isinstance(node.expression, exp.Nullif) and node.expression.expression.sql() == "0":
            changed[0] = True
            return exp.Div(this=strip_one(node.this), expression=node.expression.this)
        return node
    return tree.transform(visit), changed[0]


def _with_row_filter(tree: exp.Expression, predicate: exp.Expression) -> exp.Expression:
    def visit(node):
        if isinstance(node, exp.Filter):
            node.set("expression", exp.Where(this=exp.and_(node.expression.this, predicate.copy())))
            return node
        if isinstance(node, exp.AggFunc) and not isinstance(node.parent, exp.Filter):
            return exp.Filter(this=node, expression=exp.Where(this=predicate.copy()))
        return node
    return tree.transform(visit)


def _decompose(template: Template) -> dict:
    try:
        tree = sqlglot.parse_one(template.sql.replace(SLOT, SENTINEL), dialect=expr.DIALECT)
    except ParseError as error:
        _refuse("INFER_SYNTAX", str(error).splitlines()[0])
    if not isinstance(tree, exp.Select):
        _refuse("INFER_NOT_A_SELECT", "the template is not a single SELECT")
    if list(tree.find_all(exp.Subquery)):
        _refuse("INFER_MORE_THAN_ONE_AGGREGATION", "more than one aggregation")
    for clause in ("having", "limit", "distinct", "qualify"):
        if tree.args.get(clause):
            _refuse("INFER_UNSUPPORTED_CLAUSE", f"{clause.upper()} is not supported")
    if list(tree.find_all(exp.Window)):
        _refuse("INFER_WINDOW", "window function")
    group = tree.args.get("group")
    if group is None or [g.sql() for g in group.expressions] != [SENTINEL]:
        _refuse("INFER_GROUP_BY", "GROUP BY is not exactly the grouping slot")
    if len(tree.expressions) != 2 or tree.expressions[0].sql() != SENTINEL or tree.expressions[1].alias != "kpi_value":
        _refuse("INFER_SELECT", "SELECT is not the slot plus one aggregate expression named kpi_value")
    kpi = tree.expressions[1]
    if not list(kpi.find_all(exp.AggFunc)):
        _refuse("INFER_NO_AGGREGATE", "the KPI expression has no aggregate")
    source = tree.args["from_"].this
    if not isinstance(source, exp.Table):
        _refuse("INFER_SOURCE", "the FROM clause is not a table")
    return {"tree": tree, "source": source, "kpi": kpi.this, "where": tree.args.get("where"), "joins": tree.args.get("joins") or []}


def _table_name(table: exp.Table) -> str:
    return ".".join(p for p in (table.catalog, table.db, table.name) if p)


def _classify_filter(node: exp.Expression, index: int) -> Filter:
    """Optional filter (`:p IS NULL OR ...`), required parameter filter, or fixed row filter."""
    inner = node.this if isinstance(node, exp.Paren) else node
    params: dict[str, str] = {}

    def untyped(n):
        if isinstance(n, exp.TryCast) and isinstance(n.this, exp.Placeholder):
            params[n.this.name] = _PARAM_TYPES.get(n.to.this.name, "string")
            return exp.Placeholder(this=n.this.name)
        if isinstance(n, exp.Placeholder):
            params.setdefault(n.name, "string")
        return n

    if (isinstance(inner, exp.Or) and isinstance(inner.this, exp.Is) and isinstance(inner.this.expression, exp.Null)
            and list(inner.this.this.find_all(exp.Placeholder))):
        predicate = inner.expression.transform(untyped)
        found = sorted({p.name for p in inner.find_all(exp.Placeholder)})
        if len(found) == 1:
            return Filter(f"filter_{found[0]}", _dbx(predicate), tuple(Param(p, params.get(p, "string")) for p in found), optional=True)
    predicate = node.transform(untyped)
    names = sorted({p.name for p in predicate.find_all(exp.Placeholder)})
    if names:
        return Filter(f"filter_{'_'.join(names)}", _dbx(predicate), tuple(Param(p, params.get(p, "string")) for p in names))
    return Filter(f"fixed_{index}", _dbx(predicate))


def infer(
    templates: list[Template], *, name: str, key: str, dimensions: Mapping[str, str], engine: Engine | None = None, version: str = "1",
) -> Inference:
    """`dimensions` are the groupings the registry could inject into the slot, written in canonical form
    (bare fact columns, `<join>.<column>` for joined ones). With an engine, every join is checked against the data."""
    parts: dict[str, dict] = {}
    refused: dict[str, str] = {}
    grain: dict[str, int] | None = None
    for template in templates:
        try:
            raw = _decompose(template)
            fact_alias = raw["source"].alias_or_name
            tables = [j.this.name for j in raw["joins"]]
            aliases = {j.this.alias_or_name: (j.this.name if tables.count(j.this.name) == 1 else j.this.alias_or_name) for j in raw["joins"]}
            joins = [Join(aliases[j.this.alias_or_name], _table_name(j.this), _dbx(_canonical_columns(j.args["on"], fact_alias, aliases))) for j in raw["joins"]]
            if engine is not None and joins:
                from .backends.sqlparts import qualify, render
                checked = [(j.table, j.name, render(qualify(j.tree))) for j in joins]
                try:
                    grain = check_joins(engine, _table_name(raw["source"]), key, checked)
                except GrainError as error:
                    _refuse(error.code, error.message)
            for j in raw["joins"]:
                if (j.args.get("side") or "").upper() != "LEFT":
                    _refuse("INFER_NOT_A_LEFT_JOIN", "only LEFT JOIN keeps the fact rows; an inner join filters them")
            canonical = lambda t: _canonical_columns(t, fact_alias, aliases)  # noqa: E731
            filters = [canonical(f) for f in _conjuncts(raw["where"].this if raw["where"] else None)]
            kpi_tree, was_guarded = _guarded_division(_one_spelling(canonical(raw["kpi"])))
            parts[template.kpi_id] = {"template": template, "source": _table_name(raw["source"]), "joins": joins, "filters": filters,
                                      "kpi": kpi_tree, "guarded": was_guarded}
        except _Refusal as refusal:
            refused[template.kpi_id] = f"{refusal.code}: {refusal.message}"

    if not parts:
        raise DefinitionError("INFER_NOTHING_ACCEPTED", f"no template could be read; refused: {refused}")
    shapes = {(p["source"], tuple((j.name, j.table, j.on) for j in p["joins"])) for p in parts.values()}
    if len(shapes) != 1:
        raise DefinitionError("INFER_DIFFERENT_SOURCES", "the accepted templates read different sources or joins; infer them in separate models")
    first = next(iter(parts.values()))
    texts = {k: {_dbx(f) for f in p["filters"]} for k, p in parts.items()}
    shared_text = set.intersection(*texts.values())
    shared = [f for f in first["filters"] if _dbx(f) in shared_text]

    measures: dict[str, Measure] = {}
    kpis: list[Kpi] = []
    notes: list[str] = []
    for kpi_id, p in parts.items():
        tree = p["kpi"]
        for predicate in [f for f in p["filters"] if _dbx(f) not in shared_text]:
            tree = _with_row_filter(tree, predicate)

        def name_measure(node):
            top = isinstance(node, exp.Filter) or (isinstance(node, exp.AggFunc) and not isinstance(node.parent, exp.Filter))
            if not top:
                return node
            text = _dbx(node)
            measures.setdefault(text, Measure(f"m{len(measures) + 1}", text))
            return exp.column(measures[text].name)
        formula = _dbx(tree.transform(name_measure))
        kpis.append(Kpi(p["template"].alias, formula, status="draft"))
        if p["guarded"]:
            notes.append(f"{p['template'].alias}: the division is now guarded; a zero denominator gives NULL")
    model_filters = [_classify_filter(f, i + 1) for i, f in enumerate(shared)]
    model = SemanticModel(
        name=name, version=version, source=first["source"], key=key, measures=tuple(measures.values()), kpis=tuple(kpis),
        dimensions=tuple(Dimension(d, e) for d, e in dimensions.items()), joins=tuple(first["joins"]), filters=tuple(model_filters),
    )
    return Inference(model, {k: p["template"].alias for k, p in parts.items()}, refused, grain, notes)
