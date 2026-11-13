"""How big is the work a report asks for? Pure arithmetic on the request: no engine, O(dimensions) to compute."""
from __future__ import annotations

from dataclasses import dataclass

from .request import Report


@dataclass(frozen=True)
class Estimate:
    dimensions: int
    scopes: int              # (|rows|+1)(|cols|+1) with totals: nodes of the lattice, not rows of the result
    measures: int
    distinct_measures: int   # each needs its own state per scope: the expensive part
    aggregate_states: int    # scopes x measures: aggregate states one scan maintains per group-key family

    @property
    def description(self) -> str:
        return (f"{self.scopes} scopes x {self.measures} measures = {self.aggregate_states} aggregate states, "
                f"{self.distinct_measures} of them distinct counts")


def estimate(report: Report) -> Estimate:
    distinct = sum(1 for m in report.atoms if m.kind == "unique")
    return Estimate(len(report.dims), len(report.scopes), len(report.atoms), distinct, len(report.scopes) * len(report.atoms))
