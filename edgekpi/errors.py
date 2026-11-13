"""Every failure the library can name. One class per stage of the request lifecycle (docs: 10-edge-cases)."""
from __future__ import annotations


class KpiError(Exception):
    """Base class. `code` is stable and documented; `detail` carries machine-readable context."""

    def __init__(self, code: str, message: str, **detail):
        super().__init__(f"{code}: {message}")
        self.code, self.message, self.detail = code, message, detail


class DefinitionError(KpiError):
    """The semantic model is not valid. Raised when the model is built, never at query time."""


class RequestError(KpiError):
    """The report request is not valid for the model."""


class UnsupportedError(KpiError):
    """The model or request is valid but the chosen backend or engine cannot honour it."""


class GrainError(KpiError):
    """A join or a key breaks the one-row-per-fact guarantee."""


class EngineError(KpiError):
    """The engine failed, or returned something incomplete."""


class ReconciliationError(KpiError):
    """A returned grid violates an arithmetic invariant (docs: 16-correctness-contract)."""
