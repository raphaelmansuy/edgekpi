"""YAML <-> SemanticModel. The YAML shape is the contract with the people who own the definitions."""
from __future__ import annotations

import pathlib
import re
from typing import Any, Mapping

import yaml

from .errors import DefinitionError
from .model import Dimension, Filter, Join, Kpi, Measure, Param, SemanticModel

_TOP = {"name", "version", "source", "key", "joins", "dimensions", "measures", "kpis", "filters"}
_BOOL = "tag:yaml.org,2002:bool"


class _Loader(yaml.SafeLoader):
    """YAML 1.1 reads the key `on` as True. A join says `on:`, so only true and false are booleans here."""


_Loader.yaml_implicit_resolvers = {
    key: [(tag, rx) for tag, rx in resolvers if tag != _BOOL] for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Loader.add_implicit_resolver(_BOOL, re.compile(r"^(?:true|false)$"), list("tf"))


def _items(section: Any, what: str) -> list[tuple[str, Any]]:
    if section is None:
        return []
    if not isinstance(section, Mapping):
        raise DefinitionError("DEF_BAD_SHAPE", f"{what} is a mapping of name to definition")
    return list(section.items())


def _unknown(entry: Mapping, allowed: set[str], where: str) -> None:
    extra = sorted(set(entry) - allowed)
    if extra:
        raise DefinitionError("DEF_UNKNOWN_FIELD", f"{where}: unknown fields {extra}; allowed {sorted(allowed)}")


def from_dict(data: Mapping[str, Any]) -> SemanticModel:
    _unknown(data, _TOP, "model")
    for needed in ("name", "source", "key"):
        if needed not in data:
            raise DefinitionError("DEF_MISSING_FIELD", f"model needs {needed}")

    def expression(entry: Any, where: str, extra: set[str]) -> dict:
        if isinstance(entry, str):
            return {"expr": entry}
        _unknown(entry, {"expr", "label"} | extra, where)
        return dict(entry)

    dims = [Dimension(n, **expression(e, f"dimension {n}", set())) for n, e in _items(data.get("dimensions"), "dimensions")]
    measures = [Measure(n, **expression(e, f"measure {n}", set())) for n, e in _items(data.get("measures"), "measures")]
    kpis = []
    for name, entry in _items(data.get("kpis"), "kpis"):
        if isinstance(entry, str):
            entry = {"formula": entry}
        _unknown(entry, {"formula", "label", "owner", "status", "format"}, f"kpi {name}")
        kpis.append(Kpi(name, **entry))
    joins = []
    for name, entry in _items(data.get("joins"), "joins"):
        _unknown(entry, {"table", "on", "cardinality"}, f"join {name}")
        joins.append(Join(name, **entry))
    filters = []
    for name, entry in _items(data.get("filters"), "filters"):
        _unknown(entry, {"predicate", "params", "optional"}, f"filter {name}")
        params = tuple(Param(p, t) for p, t in (entry.get("params") or {}).items())
        filters.append(Filter(name, entry["predicate"], params, bool(entry.get("optional", False))))
    return SemanticModel(
        name=data["name"], source=data["source"], key=data["key"], version=str(data.get("version", "1")),
        measures=tuple(measures), kpis=tuple(kpis), dimensions=tuple(dims), joins=tuple(joins), filters=tuple(filters),
    )


def loads(text: str) -> SemanticModel:
    try:
        data = yaml.load(text, Loader=_Loader)  # noqa: S506 - restricted SafeLoader subclass
    except yaml.YAMLError as error:
        raise DefinitionError("DEF_YAML", str(error).splitlines()[0]) from error
    if not isinstance(data, Mapping):
        raise DefinitionError("DEF_BAD_SHAPE", "a model file is a mapping")
    return from_dict(data)


def load(path: str | pathlib.Path) -> SemanticModel:
    return loads(pathlib.Path(path).read_text())


def to_dict(model: SemanticModel) -> dict:
    """The inverse of from_dict: load(dump(m)) == m."""
    def labelled(item, extra=None):
        body = {"expr": item.expr}
        if item.label:
            body["label"] = item.label
        return body if len(body) > 1 else item.expr

    out: dict = {"name": model.name, "version": model.version, "source": model.source, "key": model.key}
    if model.joins:
        out["joins"] = {j.name: {"table": j.table, "on": j.on, "cardinality": j.cardinality} for j in model.joins}
    if model.dimensions:
        out["dimensions"] = {d.name: labelled(d) for d in model.dimensions}
    out["measures"] = {m.name: labelled(m) for m in model.measures}
    if model.kpis:
        out["kpis"] = {
            k.name: {key: value for key, value in (("formula", k.formula), ("label", k.label), ("owner", k.owner), ("status", k.status), ("format", k.format)) if value is not None}
            for k in model.kpis
        }
    if model.filters:
        out["filters"] = {f.name: {"predicate": f.predicate, "params": {p.name: p.type for p in f.params}, "optional": f.optional} for f in model.filters}
    return out


def dumps(model: SemanticModel) -> str:
    return yaml.safe_dump(to_dict(model), sort_keys=False, width=110)
