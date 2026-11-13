"""Explain one number: the measures it is made of, and what the tempting wrong answer would have been.

A reader who sees 80.0% in a total asks "why not the average of the cells above?". The answer is arithmetic on the same
grid, so no query is needed: the measures of the node and the formula (FP-L-1), set beside the mean of the children.
"""
from __future__ import annotations

from typing import Any

from sqlglot import exp

from .errors import RequestError
from .grid import Grid, Node, canon
from .request import Report


def children(grid: Grid, node: Node, report: Report) -> dict[str, list[Node]]:
    """Children of a node by the dimension added to its scope. Only scopes that exist in the grid count."""
    out: dict[str, list[Node]] = {}
    own = dict(node.key)
    for dim in report.dims:
        if dim in own:
            continue
        scope = tuple(d for d in report.dims if d in own or d == dim)
        if scope not in {n.scope for n in grid.cells}:
            continue
        kids = [n for n in grid.cells if n.scope == scope and all(dict(n.key).get(d) == v for d, v in own.items())]
        if kids:
            out[dim] = kids
    return out


def explain(report: Report, grid: Grid, kpi_name: str, scope: tuple[str, ...], members: tuple) -> dict[str, Any]:
    kpi = report.model.kpi(kpi_name)
    if kpi is None or kpi_name not in grid.kpis:
        raise RequestError("REQ_UNKNOWN_KPI", f"{kpi_name!r} is not in this result", name=kpi_name)
    node = Node(tuple(scope), tuple(canon(m) for m in members))
    values = grid.cells.get(node)
    if values is None:
        raise RequestError("REQ_UNKNOWN_NODE", f"no node {dict(node.key)} in this result")
    terms = [{"measure": name, "label": name, "kind": report.model.measure(name).kind, "value": values[name]} for name in kpi.refs]
    is_ratio = any(isinstance(n, exp.Div) for n in kpi.tree.walk())
    result: dict[str, Any] = {
        "kpi": kpi_name, "label": kpi.label or kpi_name, "format": kpi.format, "formula": kpi.formula,
        "scope": list(node.scope), "members": list(node.members), "value": values[kpi_name], "terms": terms,
        "is_ratio": is_ratio, "naive": None,
    }
    best = None
    for dim, kids in children(grid, node, report).items():
        present = [grid.cells[k][kpi_name] for k in kids if grid.cells[k][kpi_name] is not None]
        if not present:
            continue
        naive = sum(present) / len(present) if is_ratio else sum(present)
        actual = values[kpi_name]
        found = {"method": "mean" if is_ratio else "sum", "dimension": dim, "children": len(kids), "value": naive,
                 "differs": actual is None or abs(naive - actual) > 1e-9 * max(1.0, abs(actual))}
        if best is None or (found["differs"] and not best["differs"]):
            best = found                      # prefer the split where the tempting answer is actually wrong
    result["naive"] = best
    return result
