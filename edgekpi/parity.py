"""Parity: run each legacy template and the migrated model on the same data and compare every value.

This is the proof that an inferred model keeps the registry's numbers. It runs the legacy template at every grouping
(grand total included) and under several parameter bindings, then asks the library for the same nodes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any, Mapping

import sqlglot

from .backends.base import Engine, Statement
from .backends.sql import GeneratedSql
from .grid import canon
from .inference import SENTINEL, SLOT, Inference, Template, _dbx
from .request import Binding, ReportRequest
from .runner import run
from .scopes import axis_levels


@dataclass
class ParityReport:
    bindings: int = 0
    nodes: int = 0
    compared: int = 0
    null_values: int = 0
    different: list[tuple] = field(default_factory=list)
    only_after: list[tuple] = field(default_factory=list)       # nodes the library returns and the legacy query does not


def legacy_sql(template: Template, group: tuple[str, ...], legacy_dimensions: Mapping[str, str]) -> str:
    """The registry's way: paste a column list into the text. The grand total has no valid form with the slot, so that
    reference is obtained by removing the slot and the GROUP BY from the parsed tree."""
    if group:
        return template.sql.replace(SLOT, ", ".join(legacy_dimensions[g] for g in group))
    tree = sqlglot.parse_one(template.sql.replace(SLOT, SENTINEL), dialect="databricks")
    tree.set("group", None)
    tree.set("expressions", [tree.expressions[1]])
    return _dbx(tree)


def _same(a, b) -> bool:
    return (a is None and b is None) or (a is not None and b is not None and abs(float(a) - float(b)) <= 1e-12)


def verify(
    engine: Engine, templates: list[Template], inference: Inference, *, rows: tuple[str, ...], cols: tuple[str, ...],
    legacy_dimensions: Mapping[str, str], bindings: list[Mapping[str, Any]],
) -> ParityReport:
    report = ParityReport(bindings=len(bindings))
    by_id = {t.kpi_id: t for t in templates}
    kpis = tuple(inference.accepted.values())
    groupings = [r + c for r, c in product(axis_levels(rows, True), axis_levels(cols, True))]
    for binding in bindings:
        request = ReportRequest(kpis=kpis, rows=rows, cols=cols, params={k: v for k, v in binding.items() if v is not None})
        grid = run(inference.model, request, GeneratedSql(), engine).grid
        report.nodes += len(grid)
        for kpi_id, kpi_name in inference.accepted.items():
            seen = set()
            for group in groupings:
                statement = Statement(legacy_sql(by_id[kpi_id], group, legacy_dimensions), params=tuple(Binding(k, v) for k, v in binding.items()))
                for row in engine.execute(statement):
                    members = tuple(canon(row[d]) for d in group)
                    cell = grid.get(group, *members)
                    seen.add((group, members))
                    report.compared += 1
                    report.null_values += row["kpi_value"] is None
                    if cell is None or not _same(cell[kpi_name], row["kpi_value"]):
                        report.different.append((kpi_name, group, members, None if cell is None else cell[kpi_name], row["kpi_value"]))
            for node, values in grid.cells.items():
                if (node.scope, node.members) not in seen:
                    report.only_after.append((kpi_name, node.scope, node.members, values[kpi_name]))
    return report
