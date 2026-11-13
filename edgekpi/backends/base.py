"""The two contracts every approach implements, and the value objects they exchange (Dependency Inversion).

A Backend turns a validated Report into statements and turns the engine's rows back into a Grid.
An Engine runs one statement. Backends never import an engine; engines never import a backend.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol

from ..errors import EngineError
from ..grid import Grid
from ..request import Binding, Report

ROW_COUNT = "edgekpi_rows"          # hidden column: rows behind a node, so empty nodes can be dropped


@dataclass(frozen=True)
class Statement:
    text: str
    kind: str = "query"                 # "ddl" | "query"
    language: str = "sql"               # "sql" (Databricks dialect) | "malloy"
    params: tuple[Binding, ...] = ()


@dataclass(frozen=True)
class Plan:
    backend: str
    report: Report
    statements: tuple[Statement, ...]
    notes: tuple[str, ...] = ()

    @property
    def query(self) -> Statement:
        return next(s for s in reversed(self.statements) if s.kind == "query")


class Backend(ABC):
    name: str
    engines: frozenset[str]

    @abstractmethod
    def compile(self, report: Report) -> Plan: ...

    @abstractmethod
    def assemble(self, plan: Plan, rows: list[dict[str, Any]]) -> Grid: ...


class Engine(Protocol):
    name: str

    def execute(self, statement: Statement) -> list[dict[str, Any]]: ...


def assemble_flat(plan: Plan, rows: list[dict[str, Any]]) -> Grid:
    """Rows shaped `dimensions..., gid, measures..., kpis...` become nodes. Shared by the two SQL-shaped backends."""
    from ..scopes import scope_of

    report = plan.report
    grid = Grid(report.dims, tuple(m.name for m in report.atoms), tuple(k.name for k in report.kpis))
    allowed = set(report.scopes)
    for row in rows:
        if ROW_COUNT in row and not row[ROW_COUNT]:
            continue                                    # no input rows: no node (EC-L-01)
        scope = scope_of(int(row["gid"]), report.dims)
        if scope not in allowed:
            raise EngineError("ENGINE_UNEXPECTED_SCOPE", f"the engine returned a node of scope {scope}, which was not requested")
        grid.add(scope, tuple(row[d] for d in scope), row)
    return grid
