"""Self-checks that every correct pivot result passes, using only the returned rows (no second query).

Evidence for ../16-correctness-contract.md C-CHECK and the additivity probe in ../10-edgesql-integration.md.
This is a specification fixture, not product code. A passing check is necessary, not sufficient: see the
limits listed in C-CHECK and exercised in test_grid_reconciliation.py.
"""
from __future__ import annotations

from fractions import Fraction

TOLERANCE = 1e-12


def shape_of(row: dict, dims: list[str]) -> tuple[str, ...]:
    """Dimensions retained by a result row, decoded from GROUPING_ID (first listed dimension = highest bit).
    A NULL test would confuse an unknown member with a rolled-up dimension (FP-8)."""
    n = len(dims)
    return tuple(d for i, d in enumerate(dims) if not (row["gid"] >> (n - 1 - i)) & 1)


def index_nodes(rows: list[dict], dims: list[str]) -> dict:
    """Member-node key -> row. The key is (retained dimensions, their typed member values)."""
    nodes = {}
    for row in rows:
        shape = shape_of(row, dims)
        key = (shape, tuple(row[d] for d in shape))
        assert key not in nodes, f"duplicate member node {key}"
        nodes[key] = row
    return nodes


def lattice_edges(shapes) -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    """(parent, child) pairs of requested grouping shapes where the child retains exactly one more dimension.
    Grouping by a column assigns each fact row to exactly one member (NULL included), so the children of a
    parent node partition its rows."""
    shapes = sorted(set(shapes), key=lambda s: (len(s), s))
    return [(p, c) for p in shapes for c in shapes if len(c) == len(p) + 1 and set(p) < set(c)]


def relation(whole, parts) -> str:
    """How one value at a broader scope relates to the same KPI over a partition of that scope.

    equals_sum      whole = sum(parts): additive on this partition
    below_sum       max(parts) < whole < sum(parts): deduplicating (distinct-like); not a count, not a rate
    within_range    min(parts) <= whole < max(parts): intensive (rate- or average-like); not a count
    at_max          whole = max(parts) < sum(parts): ambiguous; one part contains the others, or equal rates
    uninformative   fewer than two parts, so every reading agrees
    inconsistent    none of the above: parts and whole do not describe the same population

    One observation can refute a hypothesis; it cannot confirm a business definition. A distinct count is
    additive on a partition that separates its entities, so several partitions must be probed.
    """
    parts = [p for p in parts if p is not None]
    if whole is None or len(parts) < 2:
        return "uninformative"
    total, low, high = sum(parts), min(parts), max(parts)
    if abs(whole - total) <= TOLERANCE:
        return "equals_sum"
    if abs(whole - high) <= TOLERANCE:
        return "at_max"
    if low - TOLERANCE <= whole < high:
        return "within_range"
    if high < whole < total:
        return "below_sum"
    return "inconsistent"


def reconcile(
    rows: list[dict],
    dims: list[str],
    additive: list[str],
    ratios: list[tuple[str, str, str]] = (),
    distinct: list[str] = (),
    row_count: str = "sent",
) -> list[tuple]:
    """Return every violated invariant; an empty list means the grid is internally consistent.

    I1 additive   : an additive atom at a parent equals the sum over its children, on every lattice edge.
    I2 formula    : a rate equals numerator / denominator read from the SAME node (NULL iff denominator is 0).
    I3 distinct   : max(children) <= parent <= min(sum(children), fact rows at the parent).
    I4 rate bounds: a parent rate lies between the smallest and largest child rate (mediant inequality).
    """
    nodes = index_nodes(rows, dims)
    violations = []
    for (shape, member), row in nodes.items():
        for name, numerator, denominator in ratios:
            expected = Fraction(row[numerator], row[denominator]) if row[denominator] else None
            actual = row[name]
            if (expected is None) != (actual is None) or (expected is not None and abs(float(expected) - float(actual)) > TOLERANCE):
                violations.append(("formula", name, shape, member))
    for parent, child in lattice_edges(shape for shape, _ in nodes):
        children: dict[tuple, list[dict]] = {}
        for (shape, _member), row in nodes.items():
            if shape == child:
                children.setdefault(tuple(row[d] for d in parent), []).append(row)
        parents = {member: row for (shape, member), row in nodes.items() if shape == parent}
        for member in children.keys() - parents.keys():
            violations.append(("missing_parent", parent, member, child))
        for member, row in parents.items():
            kids = children.get(member, [])
            for atom in additive:
                if sum(k[atom] for k in kids) != row[atom]:
                    violations.append(("additive", atom, parent, member, child))
            for atom in distinct:
                if kids and not max(k[atom] for k in kids) <= row[atom] <= min(sum(k[atom] for k in kids), row[row_count]):
                    violations.append(("distinct_bounds", atom, parent, member, child))
            for name, _numerator, _denominator in ratios:
                rates = [float(k[name]) for k in kids if k[name] is not None]
                if rates and row[name] is not None and not min(rates) - TOLERANCE <= float(row[name]) <= max(rates) + TOLERANCE:
                    violations.append(("rate_bounds", name, parent, member, child))
    return violations
