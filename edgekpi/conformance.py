"""Conformance: the same request through several backend/engine pairs, each compared with the independent reference."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .backends.base import Backend, Engine
from .errors import KpiError
from .model import SemanticModel
from .oracle import Diff, compare, reference
from .request import ReportRequest, validate
from .runner import run


@dataclass
class Outcome:
    label: str
    nodes: int = 0
    diffs: list[Diff] = field(default_factory=list)
    violations: list = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and not self.diffs and not self.violations


def conformance(
    model: SemanticModel, request: ReportRequest | Mapping, cases: list[tuple[str, Backend, Engine]], reference_engine: Engine,
) -> list[Outcome]:
    """Never raises for a failing case: each failure is reported in its Outcome, so one backend cannot hide another."""
    if not isinstance(request, ReportRequest):
        request = ReportRequest.from_dict(request)
    expected = reference(validate(model, request), reference_engine)
    outcomes = []
    for label, backend, engine in cases:
        outcome = Outcome(label)
        try:
            result = run(model, request, backend, engine, reconcile="flag")
            outcome.nodes, outcome.violations = len(result.grid), result.violations
            outcome.diffs = compare(result.grid, expected)
        except KpiError as error:
            outcome.error = f"{error.code}: {error.message}"
        outcomes.append(outcome)
    return outcomes
