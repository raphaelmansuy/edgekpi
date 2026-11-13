"""The independent reference: one GROUP BY per node, KPIs evaluated in Python.

It shares only the rendering of dimensions, joins and filters with the backends. It does not share the grouping
machinery (GROUPING SETS, MEASURE, nesting) or the KPI arithmetic, which are the things a backend can get wrong.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import expr
from .backends.base import Engine, Statement
from .backends.sqlparts import dimension_sql, predicate_sql, qualified_column, qualify, relation, render
from .grid import Grid, Node, canon
from .request import Report

ABS_TOL = 1e-9


@dataclass(frozen=True)
class Diff:
    kind: str                  # "missing" | "extra" | "value"
    node: tuple
    column: str | None = None
    actual: Any = None
    expected: Any = None


def reference(report: Report, engine: Engine) -> Grid:
    model = report.model
    dim_sql = dimension_sql(model)
    conjuncts = predicate_sql(report, qualified_column, dim_sql.__getitem__)
    where = " AND ".join(conjuncts) or "TRUE"
    grid = Grid(report.dims, tuple(m.name for m in report.atoms), tuple(k.name for k in report.kpis))
    for scope in report.scopes:
        select = [f"{dim_sql[d]} AS {d}" for d in scope] + ["COUNT(*) AS n"] + [f"{render(qualify(m.tree))} AS {m.name}" for m in report.atoms]
        text = f"SELECT {', '.join(select)} FROM {relation(model)} WHERE {where}"
        if scope:
            text += " GROUP BY " + ", ".join(dim_sql[d] for d in scope)
        for row in engine.execute(Statement(text, params=tuple(report.bindings.values()))):
            if not row["n"]:
                continue
            values = dict(row)
            for kpi in report.kpis:
                values[kpi.name] = expr.evaluate(kpi.tree, {m.name: row[m.name] for m in report.atoms})
            grid.add(scope, tuple(row[d] for d in scope), values)
    return grid


def compare(actual: Grid, expected: Grid) -> list[Diff]:
    diffs: list[Diff] = []
    for node in expected.cells.keys() - actual.cells.keys():
        diffs.append(Diff("missing", node.key))
    for node in actual.cells.keys() - expected.cells.keys():
        diffs.append(Diff("extra", node.key))
    for node in expected.cells.keys() & actual.cells.keys():
        for column, want in expected.cells[node].items():
            got = actual.cells[node].get(column)
            same = (got is None and want is None) or (got is not None and want is not None and abs(float(got) - float(want)) <= ABS_TOL * max(1.0, abs(float(want))))
            if not same:
                diffs.append(Diff("value", node.key, column, got, want))
    return diffs
