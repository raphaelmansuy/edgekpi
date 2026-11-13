"""The report request: what the reader asks for, validated against the model before any backend sees it."""
from __future__ import annotations

import datetime
import math
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from .errors import RequestError
from .model import Filter, Kpi, Measure, SemanticModel
from .scopes import MAX_DIMS, Scope, lattice

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FIELDS = {"kpis", "rows", "cols", "totals", "params", "where", "model_version", "published"}
MAX_IN_VALUES = 1000


@dataclass(frozen=True)
class Binding:
    """A bound parameter as it travels to the engine. Model parameters travel as STRING and are CAST in SQL."""

    name: str
    value: Any
    type: str = "STRING"


@dataclass(frozen=True)
class Where:
    dimension: str
    op: str                      # "eq" | "in"
    values: tuple


@dataclass(frozen=True)
class ReportRequest:
    kpis: tuple[str, ...]
    rows: tuple[str, ...] = ()
    cols: tuple[str, ...] = ()
    row_totals: bool = True
    col_totals: bool = True
    params: Mapping[str, Any] = field(default_factory=dict)
    where: tuple[Where, ...] = ()
    model_version: str | None = None
    published: bool = False

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReportRequest":
        unknown = sorted(set(data) - _FIELDS)
        if unknown:
            raise RequestError("REQ_UNKNOWN_FIELD", f"unknown request fields {unknown}; allowed {sorted(_FIELDS)}")
        totals = data.get("totals", {}) or {}
        where = []
        for item in data.get("where", []) or []:
            keys = set(item) - {"dim"}
            if "dim" not in item or keys not in ({"eq"}, {"in"}):
                raise RequestError("REQ_BAD_WHERE", f"a where item is {{dim, eq}} or {{dim, in}}; got {dict(item)}")
            where.append(Where(item["dim"], "eq", (item["eq"],)) if "eq" in item else Where(item["dim"], "in", tuple(item["in"])))
        return cls(
            kpis=tuple(data.get("kpis", ())), rows=tuple(data.get("rows", ())), cols=tuple(data.get("cols", ())),
            row_totals=bool(totals.get("rows", True)), col_totals=bool(totals.get("cols", True)),
            params=dict(data.get("params", {}) or {}), where=tuple(where),
            model_version=data.get("model_version"), published=bool(data.get("published", False)),
        )


@dataclass(frozen=True)
class ActiveFilter:
    filter: Filter
    bindings: tuple[Binding, ...]
    skipped: bool               # optional filter with every parameter unset: not applied


@dataclass(frozen=True)
class Report:
    """A request that passed validation. Backends read this and never the raw request."""

    model: SemanticModel
    request: ReportRequest
    dims: tuple[str, ...]
    scopes: tuple[Scope, ...]
    kpis: tuple[Kpi, ...]
    atoms: tuple[Measure, ...]
    filters: tuple[ActiveFilter, ...]
    where: tuple[tuple[Where, tuple[Binding, ...]], ...]

    @property
    def bindings(self) -> dict[str, Binding]:
        out = {b.name: b for f in self.filters for b in f.bindings}
        out.update({b.name: b for _, bs in self.where for b in bs})
        return out


def _coerce(kind: str, value: Any, name: str) -> str:
    if kind == "date":
        text = value.isoformat() if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime) else value
        if not isinstance(text, str) or not _DATE.match(text):
            raise RequestError("REQ_BAD_PARAM", f"parameter {name} is a date written YYYY-MM-DD; got {value!r}")
        try:
            datetime.date.fromisoformat(text)
        except ValueError as error:
            raise RequestError("REQ_BAD_PARAM", f"parameter {name}: {error}") from error
        return text
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise RequestError("REQ_BAD_PARAM", f"parameter {name} is an integer; got {value!r}")
        return str(value)
    if kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise RequestError("REQ_BAD_PARAM", f"parameter {name} is a finite number; got {value!r}")
        return repr(float(value))
    if not isinstance(value, str) or "\x00" in value or len(value) > 1000:
        raise RequestError("REQ_BAD_PARAM", f"parameter {name} is a string of at most 1000 characters without NUL")
    return value


def _native(value: Any, where: str) -> tuple[Any, str]:
    if value is None:
        raise RequestError("REQ_NULL_IN_FILTER", f"{where}: a NULL never matches '='/IN; filter on a real member")
    for python, sql in ((bool, "BOOLEAN"), (int, "INT"), (float, "DOUBLE"), (str, "STRING")):
        if isinstance(value, python):
            if isinstance(value, float) and not math.isfinite(value):
                break
            return value, sql
    raise RequestError("REQ_BAD_WHERE", f"{where}: unsupported value {value!r}")


def validate(model: SemanticModel, request: ReportRequest) -> Report:
    if request.model_version is not None and request.model_version != model.fingerprint():
        raise RequestError("REQ_VERSION_MISMATCH", f"the request pins model {request.model_version}, the model is {model.fingerprint()}")
    if not request.kpis:
        raise RequestError("REQ_NO_KPIS", "ask for at least one KPI")
    if len(set(request.kpis)) != len(request.kpis):
        raise RequestError("REQ_DUPLICATE_KPI", f"a KPI is requested once: {list(request.kpis)}")
    kpis = []
    for name in request.kpis:
        kpi = model.kpi(name)
        if kpi is None:
            raise RequestError("REQ_UNKNOWN_KPI", f"unknown KPI {name!r}; known: {[k.name for k in model.kpis]}", name=name)
        if request.published and kpi.status != "confirmed":
            raise RequestError("REQ_UNCONFIRMED_KPI", f"KPI {name} is {kpi.status}; a published report accepts confirmed KPIs only", name=name)
        kpis.append(kpi)
    dims = request.rows + request.cols
    for name in dims:
        if model.dimension(name) is None:
            raise RequestError("REQ_UNKNOWN_DIMENSION", f"unknown dimension {name!r}; known: {[d.name for d in model.dimensions]}", name=name)
    if len(set(dims)) != len(dims):
        raise RequestError("REQ_DUPLICATE_DIMENSION", f"a dimension sits on one axis once: {list(dims)}")
    if len(dims) > MAX_DIMS:
        raise RequestError("REQ_TOO_MANY_DIMENSIONS", f"{len(dims)} dimensions; the cap is {MAX_DIMS}")

    declared = model.params
    unknown = sorted(set(request.params) - set(declared))
    if unknown:
        raise RequestError("REQ_UNKNOWN_PARAM", f"unknown parameters {unknown}; declared {sorted(declared)}")
    active = []
    for flt in model.filters:
        values = {p.name: request.params.get(p.name) for p in flt.params}
        unset = [n for n, v in values.items() if v is None]
        if flt.params and len(unset) == len(values) and flt.optional:
            active.append(ActiveFilter(flt, tuple(Binding(n, None) for n in values), True))
            continue
        if unset:
            code = "REQ_MISSING_PARAM" if len(unset) == len(values) or not flt.optional else "REQ_PARTIAL_PARAMS"
            raise RequestError(code, f"filter {flt.name} needs {unset}", filter=flt.name)
        bindings = tuple(Binding(p.name, _coerce(p.type, values[p.name], p.name)) for p in flt.params)
        active.append(ActiveFilter(flt, bindings, False))

    where = []
    for i, w in enumerate(request.where):
        if model.dimension(w.dimension) is None:
            raise RequestError("REQ_UNKNOWN_DIMENSION", f"where: unknown dimension {w.dimension!r}", name=w.dimension)
        if not w.values or len(w.values) > MAX_IN_VALUES:
            raise RequestError("REQ_BAD_WHERE", f"where {w.dimension}: 1 to {MAX_IN_VALUES} values; got {len(w.values)}")
        bindings = []
        for j, value in enumerate(w.values):
            native, sql_type = _native(value, f"where {w.dimension}")
            bindings.append(Binding(f"w{i}_{j}", native, sql_type))
        where.append((w, tuple(bindings)))

    return Report(
        model=model, request=request, dims=dims, scopes=tuple(lattice(request.rows, request.cols, request.row_totals, request.col_totals)),
        kpis=tuple(kpis), atoms=tuple(model.atoms_of(request.kpis)), filters=tuple(active), where=tuple(where),
    )
