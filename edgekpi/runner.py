"""Run a request end to end: validate, compile, execute, assemble, reconcile. Each step is a named state."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from . import reconcile as reconciliation
from .backends.base import Backend, Engine, Plan
from .errors import EngineError, KpiError, UnsupportedError
from .grid import Grid
from .model import SemanticModel
from .request import Report, ReportRequest, validate

VALIDATED, COMPILED, EXECUTED, ASSEMBLED, RECONCILED, FAILED = "VALIDATED", "COMPILED", "EXECUTED", "ASSEMBLED", "RECONCILED", "FAILED"


@dataclass
class Result:
    report: Report | None = None
    plan: Plan | None = None
    grid: Grid | None = None
    violations: list = field(default_factory=list)
    states: list[str] = field(default_factory=list)


def run(
    model: SemanticModel,
    request: ReportRequest | Mapping,
    backend: Backend,
    engine: Engine,
    reconcile: str = "raise",
) -> Result:
    """reconcile: "raise" fails on a violated invariant, "flag" returns the violations, "off" skips the check."""
    if reconcile not in ("raise", "flag", "off"):
        raise ValueError("reconcile is 'raise', 'flag' or 'off'")
    result = Result()
    try:
        if not isinstance(request, ReportRequest):
            request = ReportRequest.from_dict(request)
        result.report = validate(model, request)
        result.states.append(VALIDATED)
        if engine.name not in backend.engines:
            raise UnsupportedError("ENGINE_MISMATCH", f"backend {backend.name} runs on {sorted(backend.engines)}, not on {engine.name}")
        result.plan = backend.compile(result.report)
        result.states.append(COMPILED)
        rows: list = []
        for statement in result.plan.statements:      # a failure here leaves no partial grid (EC-L-24)
            rows = engine.execute(statement)
        result.states.append(EXECUTED)
        result.grid = backend.assemble(result.plan, rows)
        result.states.append(ASSEMBLED)
        if reconcile != "off":
            result.violations = reconciliation.check(result.grid, model, result.report.scopes)
            if result.violations and reconcile == "raise":
                reconciliation.assert_reconciled(result.grid, model, result.report.scopes)
            result.states.append(RECONCILED)
        return result
    except KpiError as error:
        error.detail["states"] = [*result.states, FAILED]
        raise
    except Exception as error:
        raise EngineError("ENGINE_FAILED", str(error).splitlines()[0] if str(error) else type(error).__name__, states=[*result.states, FAILED]) from error
