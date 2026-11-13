"""Approach 1: a Databricks metric view. The model becomes `CREATE VIEW ... WITH METRICS`; reports are MEASURE() queries.

The view is defined once per model version (its name carries the fingerprint, so a published report keeps the
definition it was approved with). Row filters live in the report query, so the columns they read are exposed as
hidden dimensions: a metric-view query can filter on dimensions only.
"""
from __future__ import annotations

from typing import Any

import yaml
from sqlglot import exp

from .. import expr
from ..grid import Grid
from ..model import SemanticModel
from ..request import Report
from .base import ROW_COUNT, Backend, Plan, Statement, assemble_flat
from .sqlparts import predicate_sql, qualify, render, sets_sql


def _measure(name: str) -> exp.Expression:
    return exp.Anonymous(this="MEASURE", expressions=[exp.column(name)])


class MetricView(Backend):
    name = "metric-view"
    engines = frozenset({"databricks"})

    def __init__(self, catalog: str = "workspace", schema: str = "edgekpi_lib"):
        self.catalog, self.schema = catalog, schema

    def view_name(self, model: SemanticModel) -> str:
        return f"{self.catalog}.{self.schema}.edgekpi_{model.name}_{model.fingerprint()}"

    @staticmethod
    def _filter_dimensions(model: SemanticModel) -> dict[tuple[str, str], str]:
        """Hidden dimension for each raw column a filter reads, unless a dimension already is exactly that column."""
        exposed = {expr.columns(d.tree)[0]: d.name for d in model.dimensions if isinstance(d.tree, exp.Column)}
        hidden: dict[tuple[str, str], str] = {}
        for flt in model.filters:
            for key in expr.columns(flt.tree):
                if key not in exposed and key not in hidden:
                    hidden[key] = f"edgekpi_col_{key[0] or 'source'}_{key[1]}"
        return {**exposed, **hidden}

    def definition(self, model: SemanticModel) -> dict[str, Any]:
        columns = self._filter_dimensions(model)
        named = {d.name for d in model.dimensions}
        dimensions = [{"name": d.name, "expr": render(d.tree)} for d in model.dimensions]
        dimensions += [{"name": n, "expr": f"{t}.{c}" if t else c} for (t, c), n in columns.items() if n not in named]
        measures = [{"name": ROW_COUNT, "expr": "COUNT(*)"}]
        measures += [{"name": m.name, "expr": render(m.tree)} for m in model.measures]
        measures += [{"name": k.name, "expr": render(expr.guard_division(k.tree, lambda n: _measure(n)))} for k in model.kpis]
        body: dict[str, Any] = {"version": 1.1, "comment": f"edgekpi model {model.name} {model.fingerprint()}", "source": model.source}
        if model.joins:
            body["joins"] = [{"name": j.name, "source": j.table, "on": render(qualify(j.tree))} for j in model.joins]
        body.update({"dimensions": dimensions, "measures": measures})
        return body

    def ddl(self, model: SemanticModel) -> str:
        text = yaml.safe_dump(self.definition(model), sort_keys=False, width=1000)
        return f"CREATE OR REPLACE VIEW {self.view_name(model)}\nWITH METRICS LANGUAGE YAML AS $$\n{text}$$"

    def compile(self, report: Report) -> Plan:
        model = report.model
        columns = self._filter_dimensions(model)

        def dimension_column(column: exp.Column) -> exp.Expression:
            return exp.column(columns[(column.table, column.name)])

        conjuncts = predicate_sql(report, dimension_column, lambda d: d)
        select = [*report.dims]
        select.append(f"GROUPING_ID({', '.join(report.dims)}) AS gid" if report.dims else "0 AS gid")
        select += [f"MEASURE({n}) AS {n}" for n in (ROW_COUNT, *[m.name for m in report.atoms], *[k.name for k in report.kpis])]
        group = f"\nGROUP BY GROUPING SETS ({sets_sql(report.scopes, lambda d: d)})" if report.dims else ""
        query = f"SELECT {', '.join(select)}\nFROM {self.view_name(model)}" + (f"\nWHERE {' AND '.join(conjuncts)}" if conjuncts else "") + group
        return Plan(
            self.name, report,
            (Statement(self.ddl(model), kind="ddl"), Statement(query, params=tuple(report.bindings.values()))),
            ("measures and KPI formulas are evaluated inside the view; the query only groups",),
        )

    def assemble(self, plan: Plan, rows: list[dict[str, Any]]) -> Grid:
        return assemble_flat(plan, rows)
