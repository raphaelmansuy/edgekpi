"""The semantic model: typed, frozen, validated when built. One definition feeds all three backends."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Iterable

from sqlglot import exp

from . import expr
from .errors import DefinitionError

PARAM_TYPES = {"date": "DATE", "string": "STRING", "int": "INT", "number": "DOUBLE"}
STATUSES = ("confirmed", "unconfirmed", "draft")
ADDITIVE = ("count", "sum")


@lru_cache(maxsize=None)
def _row(text: str, where: str, placeholders: bool) -> exp.Expression:
    return expr.row_expression(text, where, placeholders)


@lru_cache(maxsize=None)
def _measure(text: str, where: str) -> exp.Expression:
    return expr.measure_expression(text, where)


@lru_cache(maxsize=None)
def _formula(text: str, where: str) -> exp.Expression:
    return expr.formula(text, where)


def _ident(value: str, what: str) -> None:
    if not isinstance(value, str) or not expr.IDENT.match(value):
        raise DefinitionError("DEF_BAD_IDENTIFIER", f"{what} {value!r} must match [A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True)
class Param:
    name: str
    type: str = "string"


@dataclass(frozen=True)
class Join:
    """A many-to-one join from the fact. `on` writes fact columns bare and joined columns as `<name>.<column>`."""

    name: str
    table: str
    on: str
    cardinality: str = "one"

    @property
    def tree(self) -> exp.Expression:
        return _row(self.on, f"join {self.name}", False).copy()


@dataclass(frozen=True)
class Dimension:
    name: str
    expr: str
    label: str | None = None

    @property
    def tree(self) -> exp.Expression:
        return _row(self.expr, f"dimension {self.name}", False).copy()


@dataclass(frozen=True)
class Measure:
    name: str
    expr: str
    label: str | None = None

    @property
    def tree(self) -> exp.Expression:
        return _measure(self.expr, f"measure {self.name}").copy()

    @property
    def kind(self) -> str:
        return expr.measure_kind(self.tree)

    @property
    def additive(self) -> bool:
        """Parts add up to the whole. False for distinct counts, averages, minima and maxima."""
        return self.kind in ADDITIVE


@dataclass(frozen=True)
class Kpi:
    name: str
    formula: str
    label: str | None = None
    owner: str | None = None
    status: str = "unconfirmed"
    format: str = "number"            # "number" | "percent": presentation hint only

    @property
    def tree(self) -> exp.Expression:
        return _formula(self.formula, f"kpi {self.name}").copy()

    @property
    def refs(self) -> list[str]:
        return expr.formula_refs(self.tree)


@dataclass(frozen=True)
class Filter:
    """A row filter applied to every report. `:name` marks a bound parameter. Optional: skipped when every
    parameter is unset. Required: refused at request time when a parameter is missing."""

    name: str
    predicate: str
    params: tuple[Param, ...] = ()
    optional: bool = False

    @property
    def tree(self) -> exp.Expression:
        return _row(self.predicate, f"filter {self.name}", True).copy()


@dataclass(frozen=True)
class SemanticModel:
    name: str
    source: str
    key: str
    measures: tuple[Measure, ...]
    kpis: tuple[Kpi, ...] = ()
    dimensions: tuple[Dimension, ...] = ()
    joins: tuple[Join, ...] = ()
    filters: tuple[Filter, ...] = ()
    version: str = "1"

    def __post_init__(self):
        _ident(self.name, "model name")
        _ident(self.key, "key column")
        if not expr.TABLE.match(self.source or ""):
            raise DefinitionError("DEF_BAD_IDENTIFIER", f"source {self.source!r} must be a table name, optionally catalog.schema.table")
        if not self.measures:
            raise DefinitionError("DEF_NO_MEASURES", "a model needs at least one measure")
        names = [d.name for d in self.dimensions] + [m.name for m in self.measures] + [k.name for k in self.kpis]
        for name in names:
            _ident(name, "name")
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise DefinitionError("DEF_DUPLICATE_NAME", f"dimensions, measures and KPIs share one namespace; repeated: {duplicates}")
        reserved = [n for n in names + [j.name for j in self.joins] if n.lower() in (expr.FACT, "edgekpi_rows", "gid")]
        if reserved:
            raise DefinitionError("DEF_RESERVED_NAME", f"{reserved} are reserved")

        join_names = [j.name for j in self.joins]
        for join in self.joins:
            _ident(join.name, "join name")
            if not expr.TABLE.match(join.table):
                raise DefinitionError("DEF_BAD_IDENTIFIER", f"join table {join.table!r}")
            if join.cardinality != "one":
                raise DefinitionError("DEF_JOIN_CARDINALITY", f"join {join.name}: only many-to-one joins keep the grain; got {join.cardinality!r}")
        if len(set(join_names)) != len(join_names):
            raise DefinitionError("DEF_DUPLICATE_NAME", f"join names repeat: {join_names}")

        def qualifiers(tree: exp.Expression, where: str, allowed: Iterable[str]):
            for table, column in expr.columns(tree):
                if table and table not in allowed:
                    raise DefinitionError("DEF_UNKNOWN_QUALIFIER", f"{where}: {table}.{column} names no join", qualifier=table)

        for index, join in enumerate(self.joins):
            qualifiers(join.tree, f"join {join.name}", join_names[: index + 1])
        for item in (*self.dimensions, *self.measures):
            qualifiers(item.tree, f"{type(item).__name__.lower()} {item.name}", join_names)
        measure_names = {m.name for m in self.measures}
        for kpi in self.kpis:
            if kpi.status not in STATUSES:
                raise DefinitionError("DEF_BAD_STATUS", f"kpi {kpi.name}: status {kpi.status!r} not in {STATUSES}")
            missing = [r for r in kpi.refs if r not in measure_names]
            if missing:
                raise DefinitionError("DEF_UNKNOWN_MEASURE", f"kpi {kpi.name} uses unknown measures {missing}", missing=missing)
        filter_names = [f.name for f in self.filters]
        if len(set(filter_names)) != len(filter_names):
            raise DefinitionError("DEF_DUPLICATE_NAME", f"filter names repeat: {filter_names}")
        owner: dict[str, str] = {}
        for flt in self.filters:
            _ident(flt.name, "filter name")
            declared = {p.name for p in flt.params}
            for param in flt.params:
                _ident(param.name, "parameter name")
                if param.type not in PARAM_TYPES:
                    raise DefinitionError("DEF_BAD_PARAM_TYPE", f"filter {flt.name}: parameter {param.name} has type {param.type!r}; use {sorted(PARAM_TYPES)}")
                if owner.setdefault(param.name, flt.name) != flt.name:
                    raise DefinitionError("DEF_DUPLICATE_NAME", f"parameter {param.name} is declared by {owner[param.name]} and {flt.name}")
            used = {p.name for p in flt.tree.find_all(exp.Placeholder)}
            if used != declared:
                raise DefinitionError("DEF_PARAM_MISMATCH", f"filter {flt.name}: placeholders {sorted(used)} differ from declared parameters {sorted(declared)}")
            if flt.optional and not declared:
                raise DefinitionError("DEF_PARAM_MISMATCH", f"filter {flt.name}: an optional filter needs a parameter to be optional on")
            qualifiers(flt.tree, f"filter {flt.name}", join_names)

    # lookups -----------------------------------------------------------------------------------------------
    def dimension(self, name: str) -> Dimension | None:
        return next((d for d in self.dimensions if d.name == name), None)

    def measure(self, name: str) -> Measure | None:
        return next((m for m in self.measures if m.name == name), None)

    def kpi(self, name: str) -> Kpi | None:
        return next((k for k in self.kpis if k.name == name), None)

    @property
    def params(self) -> dict[str, Param]:
        return {p.name: p for f in self.filters for p in f.params}

    def atoms_of(self, kpi_names: Iterable[str]) -> list[Measure]:
        """The measures behind the requested KPIs, each once, in definition order."""
        needed = {r for name in kpi_names for r in self.kpi(name).refs}
        return [m for m in self.measures if m.name in needed]

    def fingerprint(self) -> str:
        """Stable content hash. A request may pin it; a changed definition then fails instead of drifting."""
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True, default=str).encode()).hexdigest()[:12]
