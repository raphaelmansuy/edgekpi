"""Approach 3: generated SQL. One statement, one scan, every requested grouping set, planned from the model."""
from __future__ import annotations

from typing import Any

from sqlglot import exp

from .. import expr
from ..grid import Grid
from ..request import Report
from ..scopes import gid
from .base import ROW_COUNT, Backend, Plan, Statement, assemble_flat
from .sqlparts import dimension_sql, predicate_sql, qualified_column, qualify, relation, render, sets_sql


class GeneratedSql(Backend):
    name = "sql"
    engines = frozenset({"duckdb", "databricks"})

    def compile(self, report: Report) -> Plan:
        model = report.model
        dim_sql = dimension_sql(model)
        refs = [dim_sql[d] for d in report.dims]
        conjuncts = predicate_sql(report, qualified_column, dim_sql.__getitem__)

        select = [f"{dim_sql[d]} AS {d}" for d in report.dims]
        select.append(f"GROUPING_ID({', '.join(refs)}) AS gid" if refs else "0 AS gid")
        select.append(f"COUNT(*) AS {ROW_COUNT}")
        select += [f"{render(qualify(m.tree))} AS {m.name}" for m in report.atoms]
        group = f"\n  GROUP BY GROUPING SETS ({sets_sql(report.scopes, dim_sql.__getitem__)})" if refs else ""
        outer = [*report.dims, "gid", ROW_COUNT, *[m.name for m in report.atoms]]
        # a KPI is a function of the measures of the same node, applied AFTER aggregation (docs: 04, R3)
        outer += [f"{render(expr.guard_division(k.tree, lambda name: exp.column(name)))} AS {k.name}" for k in report.kpis]
        text = (
            "WITH agg AS (\n  SELECT " + ",\n    ".join(select)
            + f"\n  FROM {relation(model)}\n  WHERE " + ("\n    AND ".join(conjuncts) or "TRUE")
            + group + "\n  HAVING COUNT(*) > 0\n)\nSELECT " + ", ".join(outer) + "\nFROM agg"
        )
        return Plan(self.name, report, (Statement(text, params=tuple(report.bindings.values())),),
                    (f"{len(report.scopes)} grouping sets in one scan",))

    def assemble(self, plan: Plan, rows: list[dict[str, Any]]) -> Grid:
        return assemble_flat(plan, rows)
