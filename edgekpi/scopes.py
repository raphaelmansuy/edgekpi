"""The scope model: which groupings a report needs, and how a grouping is identified.

A scope is the tuple of dimensions a node is grouped by. Rows and columns each form a ROLLUP, and the report is
their cross product (docs: 05-domain-model, ART-LATTICE). Planning, assembly and estimates all use this module.
"""
from __future__ import annotations

from itertools import product

MAX_DIMS = 8

Scope = tuple[str, ...]


def axis_levels(dims: tuple[str, ...], totals: bool) -> list[Scope]:
    """(a, b, c), (a, b), (a), () with totals; only (a, b, c) without."""
    if not totals:
        return [tuple(dims)]
    return [tuple(dims[:k]) for k in range(len(dims), -1, -1)]


def lattice(rows: tuple[str, ...], cols: tuple[str, ...], row_totals: bool = True, col_totals: bool = True) -> list[Scope]:
    """Every requested scope, each ordered like rows + cols. Count: (|rows|+1)(|cols|+1) with totals."""
    return [r + c for r, c in product(axis_levels(rows, row_totals), axis_levels(cols, col_totals))]


def gid(scope: Scope, dims: tuple[str, ...]) -> int:
    """GROUPING_ID of a scope: bit set when the dimension is rolled up. First dimension is the highest bit."""
    return sum(1 << (len(dims) - 1 - i) for i, d in enumerate(dims) if d not in scope)


def scope_of(identifier: int, dims: tuple[str, ...]) -> Scope:
    return tuple(d for i, d in enumerate(dims) if not identifier >> (len(dims) - 1 - i) & 1)
