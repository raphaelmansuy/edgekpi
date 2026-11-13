"""The result of a report: a long table of nodes keyed by scope and member values, never a presentation pivot."""
from __future__ import annotations

import datetime
import decimal
from dataclasses import dataclass, field
from typing import Any

from .scopes import Scope


def canon(value: Any) -> Any:
    """One representation per member or value, whatever the engine returned (docs: EC-L-30)."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        value = float(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


@dataclass(frozen=True)
class Node:
    """A grouping and the member of each of its dimensions. NULL member and rolled-up total never collide:
    a rolled-up dimension is absent from `scope`; a NULL member is present with value None."""

    scope: Scope
    members: tuple

    @property
    def key(self) -> tuple:
        return tuple(zip(self.scope, self.members))


@dataclass
class Grid:
    dims: tuple[str, ...]
    measures: tuple[str, ...]
    kpis: tuple[str, ...]
    cells: dict[Node, dict[str, Any]] = field(default_factory=dict)

    def add(self, scope: Scope, members: tuple, values: dict[str, Any]) -> None:
        node = Node(scope, tuple(canon(m) for m in members))
        if node in self.cells:
            raise ValueError(f"node {node.key} appears twice in one result")
        self.cells[node] = {name: canon(values.get(name)) for name in (*self.measures, *self.kpis)}

    def get(self, scope: Scope, *members) -> dict[str, Any] | None:
        return self.cells.get(Node(tuple(scope), tuple(canon(m) for m in members)))

    def __len__(self) -> int:
        return len(self.cells)

    def long_rows(self) -> list[dict[str, Any]]:
        """Presentation-neutral: one dict per node, rolled-up dimensions as None plus an explicit `scope`."""
        rows = []
        for node, values in self.cells.items():
            row = {d: None for d in self.dims}
            row.update(zip(node.scope, node.members))
            rows.append({**row, "scope": ",".join(node.scope) or "(total)", **values})
        return rows
