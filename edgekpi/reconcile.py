"""Arithmetic invariants every complete grid must satisfy. A violation names the node (docs: 11-correctness C-CHECK).

  C-PARTS  an additive measure of a node equals the sum over its children (a dimension added to the scope)
  C-BOUND  a distinct count lies between the largest child and the sum of the children
  C-RATE   each KPI equals its formula applied to the measures of the SAME node, recomputed here in Python

Cost is O(nodes x dimensions): one pass indexing children by parent, one pass comparing.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from . import expr
from .errors import ReconciliationError
from .grid import Grid, Node
from .model import SemanticModel

REL_TOL = 1e-9


@dataclass(frozen=True)
class Violation:
    code: str
    node: tuple
    message: str


def _close(a, b) -> bool:
    return abs(float(a) - float(b)) <= REL_TOL * max(1.0, abs(float(a)), abs(float(b)))


def check(grid: Grid, model: SemanticModel, requested=None) -> list[Violation]:
    """`requested` are the scopes the report asked for; a node missing from them is a hole, not an absent scope."""
    violations: list[Violation] = []
    scopes = set(requested) if requested is not None else {n.scope for n in grid.cells}
    additive = [m for m in grid.measures if model.measure(m).additive]
    unique = [m for m in grid.measures if model.measure(m).kind == "unique"]

    children: dict[Node, list[Node]] = defaultdict(list)
    for node in grid.cells:
        for position, dim in enumerate(node.scope):
            parent_scope = node.scope[:position] + node.scope[position + 1:]
            if parent_scope in scopes:
                children[Node(parent_scope, node.members[:position] + node.members[position + 1:])].append(node)

    for parent, kids in children.items():
        values = grid.cells.get(parent)
        if values is None:
            violations.append(Violation("C-PARTS", parent.key, f"{len(kids)} children exist but the parent node is missing"))
            continue
        # one dimension is added per step; groups of children that differ by that dimension partition the parent
        by_dim: dict[str, list[Node]] = defaultdict(list)
        for kid in kids:
            added = next(d for d in kid.scope if d not in parent.scope)
            by_dim[added].append(kid)
        for added, group in by_dim.items():
            for name in additive:
                total = sum(grid.cells[k][name] or 0 for k in group)
                if not _close(total, values[name] or 0):
                    violations.append(Violation("C-PARTS", parent.key, f"{name}: children by {added} add to {total}, the node says {values[name]}"))
            for name in unique:
                parts = [grid.cells[k][name] or 0 for k in group]
                if not (max(parts) <= (values[name] or 0) <= sum(parts)):
                    violations.append(Violation("C-BOUND", parent.key, f"{name}: {values[name]} is outside [{max(parts)}, {sum(parts)}] given children by {added}"))

    for node, values in grid.cells.items():
        for kpi_name in grid.kpis:
            expected = expr.evaluate(model.kpi(kpi_name).tree, {m: values[m] for m in grid.measures})
            actual = values[kpi_name]
            if (expected is None) != (actual is None) or (expected is not None and not _close(expected, actual)):
                violations.append(Violation("C-RATE", node.key, f"{kpi_name} is {actual}, its measures give {expected}"))
    return violations


def assert_reconciled(grid: Grid, model: SemanticModel, requested=None) -> None:
    violations = check(grid, model, requested)
    if violations:
        first = violations[0]
        raise ReconciliationError(first.code, f"{len(violations)} violation(s); first at {dict(first.node)}: {first.message}", violations=violations)
