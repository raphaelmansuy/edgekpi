"""Expressions of the semantic model: parse once, validate against a whitelist, rewrite in one place.

Everything a user writes (dimension, measure, filter, KPI formula) is parsed with sqlglot in the Databricks
dialect and checked node by node. Anything outside the whitelist is refused with the name of the construct.
Text is never concatenated into SQL: backends render from the validated tree (docs: 03-architecture, EC-L-07/10).
"""
from __future__ import annotations

import re
from typing import Callable

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from .errors import DefinitionError

DIALECT = "databricks"
FACT = "source"                      # alias of the fact table in generated SQL; reserved, never a join name
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){0,2}$")

_ROW = (
    exp.Column, exp.Identifier, exp.Literal, exp.Boolean, exp.Null, exp.Paren, exp.Neg, exp.Add, exp.Sub, exp.Mul,
    exp.Div, exp.Mod, exp.And, exp.Or, exp.Not, exp.EQ, exp.NEQ, exp.GT, exp.GTE, exp.LT, exp.LTE, exp.Is, exp.In,
    exp.Between, exp.Like, exp.Case, exp.If, exp.Cast, exp.TryCast, exp.DataType, exp.Coalesce, exp.Nullif,
    exp.Upper, exp.Lower, exp.Abs, exp.Round, exp.Year, exp.Month, exp.Day, exp.TsOrDsToDate, exp.TimestampTrunc,
    exp.Var, exp.Tuple,
)
_AGG = (exp.Count, exp.CountIf, exp.Sum, exp.Avg, exp.Min, exp.Max)
_MEASURE_PARTS = (exp.Filter, exp.Where, exp.Distinct, exp.Star)
_FORMULA = (exp.Column, exp.Identifier, exp.Literal, exp.Paren, exp.Neg, exp.Add, exp.Sub, exp.Mul, exp.Div)
KINDS = {exp.Count: "count", exp.CountIf: "count", exp.Sum: "sum", exp.Avg: "avg", exp.Min: "min", exp.Max: "max"}


def parse(text: str, where: str) -> exp.Expression:
    if not isinstance(text, str) or not text.strip():
        raise DefinitionError("DEF_EMPTY_EXPRESSION", f"{where}: the expression is empty")
    try:
        return sqlglot.parse_one(text, dialect=DIALECT)
    except ParseError as error:
        raise DefinitionError("DEF_SYNTAX", f"{where}: {str(error).splitlines()[0]}") from error


def _refuse_outside(tree: exp.Expression, allowed: tuple, where: str) -> None:
    for node in tree.walk():
        if not isinstance(node, allowed):
            raise DefinitionError("DEF_UNSUPPORTED_CONSTRUCT", f"{where}: {type(node).__name__} is not supported", construct=type(node).__name__)


def row_expression(text: str, where: str, placeholders: bool = False) -> exp.Expression:
    """A value computed per source row: dimension expression or filter predicate. No aggregate, no subquery."""
    tree = parse(text, where)
    _refuse_outside(tree, _ROW + ((exp.Placeholder,) if placeholders else ()), where)
    return tree


def measure_expression(text: str, where: str) -> exp.Expression:
    """Exactly one aggregate (optionally FILTERed) over a row-level argument."""
    tree = parse(text, where)
    aggregate, predicate = tree, None
    if isinstance(tree, exp.Filter):
        aggregate, predicate = tree.this, tree.expression.this
    if not isinstance(aggregate, _AGG):
        raise DefinitionError("DEF_NOT_AN_AGGREGATE", f"{where}: a measure is one aggregate such as COUNT, SUM or COUNT(DISTINCT), not {type(aggregate).__name__}")
    for part in (aggregate.this, predicate):
        if part is not None and any(isinstance(n, _AGG) for n in part.walk()):
            raise DefinitionError("DEF_NESTED_AGGREGATE", f"{where}: an aggregate cannot contain another aggregate")
    _refuse_outside(tree, _ROW + _AGG + _MEASURE_PARTS, where)
    return tree


def measure_kind(tree: exp.Expression) -> str:
    aggregate = tree.this if isinstance(tree, exp.Filter) else tree
    if isinstance(aggregate, exp.Count) and isinstance(aggregate.this, exp.Distinct):
        return "unique"
    return KINDS[type(aggregate)]


def formula(text: str, where: str) -> exp.Expression:
    """A KPI formula: arithmetic over measure names. `ratio(n, d)` is the guarded division."""
    tree = parse(text, where)

    def ratio(node):
        if isinstance(node, exp.Anonymous) and node.name.lower() == "ratio":
            if len(node.expressions) != 2:
                raise DefinitionError("DEF_BAD_RATIO", f"{where}: ratio(numerator, denominator) takes two arguments")
            return exp.Div(this=node.expressions[0], expression=node.expressions[1])
        return node

    tree = tree.transform(ratio)
    _refuse_outside(tree, _FORMULA, where)
    for column in tree.find_all(exp.Column):
        if column.table:
            raise DefinitionError("DEF_QUALIFIED_REFERENCE", f"{where}: a formula refers to measures by bare name, not {column.sql()}")
    return tree


def formula_refs(tree: exp.Expression) -> list[str]:
    seen: list[str] = []
    for column in tree.find_all(exp.Column):
        if column.name not in seen:
            seen.append(column.name)
    return seen


def columns(tree: exp.Expression) -> list[tuple[str, str]]:
    return [(c.table, c.name) for c in tree.find_all(exp.Column)]


def _wrap(node: exp.Expression) -> exp.Expression:
    return exp.Paren(this=node) if isinstance(node, (exp.Add, exp.Sub, exp.Mul, exp.Div)) else node


def guard_division(tree: exp.Expression, reference: Callable[[str], exp.Expression]) -> exp.Expression:
    """Substitute each measure name through `reference` and write every division as n * 1.0 / NULLIF(d, 0).
    The only place a zero denominator is handled, so no backend can forget it (docs: EC-L-02)."""
    def visit(node: exp.Expression) -> exp.Expression:
        if isinstance(node, exp.Column):
            return reference(node.name)
        if isinstance(node, exp.Div):
            numerator = exp.Mul(this=_wrap(visit(node.this)), expression=exp.Literal.number("1.0"))
            denominator = exp.Nullif(this=_wrap(visit(node.expression)), expression=exp.Literal.number(0))
            return exp.Div(this=numerator, expression=denominator)
        copy = node.copy()
        for key, value in node.args.items():
            if isinstance(value, exp.Expression):
                copy.set(key, visit(value))
            elif isinstance(value, list):
                copy.set(key, [visit(v) if isinstance(v, exp.Expression) else v for v in value])
        return copy
    return visit(tree)


def evaluate(tree: exp.Expression, values: dict[str, float | int | None]):
    """Independent Python evaluation of a formula. None propagates; a zero denominator gives None."""
    if isinstance(tree, exp.Paren):
        return evaluate(tree.this, values)
    if isinstance(tree, exp.Column):
        return values[tree.name]
    if isinstance(tree, exp.Literal):
        return float(tree.this) if "." in tree.this else int(tree.this)
    if isinstance(tree, exp.Neg):
        inner = evaluate(tree.this, values)
        return None if inner is None else -inner
    a, b = evaluate(tree.this, values), evaluate(tree.expression, values)
    if a is None or b is None:
        return None
    if isinstance(tree, exp.Add):
        return a + b
    if isinstance(tree, exp.Sub):
        return a - b
    if isinstance(tree, exp.Mul):
        return a * b
    return None if b == 0 else a / b


def to_sql(tree: exp.Expression, dialect: str = DIALECT) -> str:
    return tree.sql(dialect=dialect)
