"""Spike: the smallest planner that can answer reporting scenarios S1 to S4 in ONE scan.

This is evidence for the specification, not the product implementation.
Spec homes: ../07-planner-and-sql-generation.md (PLAN-*), ../06-semantic-model-and-dsl.md (SEM-*).

Deliberate simplifications, each replaced in the real implementation (../13-implementation-plan.md):
  * atoms and KPI formulas are strings here. The product stores a typed tree (SEM-AST) and
    never concatenates user text (KILL-12). Everything below comes from trusted fixtures.
  * one fact table, no joins. Multi-fact drill-across is PLAN-DRILL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import product


MAX_DIMS = 8  # PLAN_TOO_MANY_DIMS: a pivot beyond this is a cube request, not a report (EC-GSET-EXPLOSION)


@dataclass(frozen=True)
class Atom:
    """Level 0 measure: one aggregate over one fact (SEM-L0)."""

    name: str
    expr: str  # SQL aggregate, FILTER allowed


@dataclass(frozen=True)
class Kpi:
    """Level 1 KPI: a scalar function of atoms, evaluated AFTER aggregation (SEM-L1, R3)."""

    name: str
    formula: str  # e.g. "{delivered} / NULLIF({sent}, 0)"

    def atoms(self) -> set[str]:
        return set(re.findall(r"\{(\w+)\}", self.formula))

    @classmethod
    def ratio(cls, name: str, numerator: str, denominator: str) -> Kpi:
        """The only way to write a ratio: the zero-denominator guard is generated once (DRY, EC-DIV0).
        Databricks runs ANSI mode by default, where a bare `/ 0` raises DIVIDE_BY_ZERO."""
        return cls(name, f"{{{numerator}}} * 1.0 / NULLIF({{{denominator}}}, 0)")


def axis_levels(dims: list[str], totals: bool) -> list[tuple[str, ...]]:
    """ROLLUP levels of one axis: (a,b,c), (a,b), (a), (). Without totals only the detail level."""
    if not totals:
        return [tuple(dims)]
    return [tuple(dims[:k]) for k in range(len(dims), -1, -1)]


def grouping_sets(
    row_dims: list[str], col_dims: list[str], row_totals: bool = True, col_totals: bool = True
) -> list[tuple[str, ...]]:
    """Cross product of row levels and column levels = the requested nodes of the lattice (ART-LATTICE)."""
    sets = []
    for r, c in product(axis_levels(row_dims, row_totals), axis_levels(col_dims, col_totals)):
        sets.append(tuple(r) + tuple(c))
    return sets


def plan_sql(
    table: str,
    atoms: list[Atom],
    kpis: list[Kpi],
    row_dims: list[str],
    col_dims: list[str],
    where: str = "TRUE",
    row_totals: bool = True,
    col_totals: bool = True,
) -> str:
    """One statement, one scan of `table`, every requested grouping set, GROUPING_ID as node identity."""
    known = {a.name for a in atoms}
    for k in kpis:  # fail closed on an unknown atom (EC-DEP-01)
        missing = k.atoms() - known
        if missing:
            raise ValueError(f"KPI {k.name} uses unknown atoms {sorted(missing)}")
    dims = row_dims + col_dims
    if len(set(dims)) != len(dims):
        raise ValueError(f"PLAN_DUPLICATE_DIM: a dimension may sit on one axis once: {dims}")
    if len(dims) > MAX_DIMS:
        raise ValueError(f"PLAN_TOO_MANY_DIMS: {len(dims)} dimensions, cap is {MAX_DIMS}")
    sets = grouping_sets(row_dims, col_dims, row_totals, col_totals)
    set_sql = ", ".join("(" + ", ".join(s) + ")" for s in sets)
    atom_sql = ",\n    ".join(f"{a.expr} AS {a.name}" for a in atoms)
    kpi_cols = [f"{k.formula.format(**{a: a for a in k.atoms()})} AS {k.name}" for k in kpis]
    dim_list = ", ".join(dims)
    atom_cols = ", ".join(a.name for a in atoms)
    return f"""WITH agg AS (
  SELECT {dim_list},
    GROUPING_ID({dim_list}) AS gid,
    {atom_sql}
  FROM {table}
  WHERE {where}
  GROUP BY GROUPING SETS ({set_sql})
  HAVING COUNT(*) > 0
)
SELECT {", ".join([dim_list, "gid", atom_cols] + kpi_cols)}
FROM agg"""


def oracle_sql(table: str, atoms: list[Atom], dims_in_set: tuple[str, ...], where: str = "TRUE") -> str:
    """Baseline: ONE independent GROUP BY per node. Used only as the parity oracle (article: naive oracle)."""
    atom_sql = ", ".join(f"{a.expr} AS {a.name}" for a in atoms)
    if dims_in_set:
        cols = ", ".join(dims_in_set)
        return f"SELECT {cols}, {atom_sql} FROM {table} WHERE {where} GROUP BY {cols}"
    return f"SELECT {atom_sql} FROM {table} WHERE {where}"


@dataclass(frozen=True)
class Part:
    """One fact of a drill-across request (PLAN-DRILL). `source` may be a table or a parenthesised subquery."""

    name: str
    source: str
    atoms: tuple[Atom, ...]
    where: str = "TRUE"


def drill_across_sql(parts: list[Part], dims: list[str], sets: list[tuple[str, ...]]) -> str:
    """Aggregate every fact to the SAME grouping sets, then join on node identity (GROUPING_ID + IS NOT DISTINCT FROM on dims).
    No detail row of one fact ever meets a detail row of another, so nothing fans out (FP-6, article R5)."""
    dim_list = ", ".join(dims)
    set_sql = ", ".join("(" + ", ".join(s) + ")" for s in sets)
    ctes, keys = [], []
    for p in parts:
        atom_sql = ", ".join(f"{a.expr} AS {a.name}" for a in p.atoms)
        ctes.append(
            f"{p.name} AS (SELECT {dim_list}, GROUPING_ID({dim_list}) AS gid, {atom_sql} "
            f"FROM {p.source} WHERE {p.where} GROUP BY GROUPING SETS ({set_sql}) HAVING COUNT(*) > 0)"
        )
        keys.append(f"SELECT {dim_list}, gid FROM {p.name}")
    ctes.append("node AS (" + " UNION ".join(keys) + ")")
    joins = "\n".join(
        f"LEFT JOIN {p.name} ON {p.name}.gid = node.gid AND "
        + " AND ".join(f"{p.name}.{d} IS NOT DISTINCT FROM node.{d}" for d in dims)
        for p in parts
    )
    cols = ", ".join(f"{p.name}.{a.name}" for p in parts for a in p.atoms)
    return "WITH " + ",\n".join(ctes) + f"\nSELECT {', '.join('node.' + d for d in dims)}, node.gid, {cols}\nFROM node\n{joins}"
