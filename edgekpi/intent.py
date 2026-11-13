"""For an AI assistant: the catalogue it may choose from, a JSON Schema that constrains its output, and a resolver
that turns a loose proposal into a validated request or into questions. Free text never reaches SQL: only known ids do."""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Any, Mapping

from .errors import RequestError
from .model import SemanticModel
from .request import ReportRequest, validate

_JSON_TYPES = {"date": {"type": "string", "format": "date"}, "string": {"type": "string"}, "int": {"type": "integer"}, "number": {"type": "number"}}


def catalog(model: SemanticModel) -> dict[str, Any]:
    """What the assistant may mention. Labels are data, never instructions: they are quoted, not interpreted."""
    return {
        "model": model.name, "version": model.fingerprint(),
        "kpis": [{"id": k.name, "label": k.label or k.name, "status": k.status} for k in model.kpis],
        "dimensions": [{"id": d.name, "label": d.label or d.name} for d in model.dimensions],
        "parameters": {name: p.type for name, p in model.params.items()},
    }


def request_json_schema(model: SemanticModel) -> dict[str, Any]:
    """Structured-output schema: ids are enums, so the assistant cannot invent a KPI or a dimension."""
    kpis, dims = [k.name for k in model.kpis], [d.name for d in model.dimensions]
    axis = {"type": "array", "items": {"enum": dims}, "uniqueItems": True, "maxItems": 8}
    return {
        "type": "object", "additionalProperties": False, "required": ["kpis"],
        "properties": {
            "kpis": {"type": "array", "items": {"enum": kpis}, "uniqueItems": True, "minItems": 1},
            "rows": axis, "cols": axis,
            "totals": {"type": "object", "additionalProperties": False, "properties": {"rows": {"type": "boolean"}, "cols": {"type": "boolean"}}},
            "params": {"type": "object", "additionalProperties": False, "properties": {n: _JSON_TYPES[p.type] for n, p in model.params.items()}},
            "where": {"type": "array", "items": {"type": "object", "required": ["dim"], "properties": {"dim": {"enum": dims}, "eq": {}, "in": {"type": "array"}}}},
        },
    }


@dataclass
class Resolution:
    request: ReportRequest | None
    questions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _resolve_name(text: Any, options: dict[str, str], kind: str, notes: list[str], questions: list[str]) -> str | None:
    """options maps id -> label. Exact id, then exact label (case-insensitive), then a single close match."""
    if not isinstance(text, str):
        questions.append(f"a {kind} must be given by name; got {text!r}")
        return None
    if text in options:
        return text
    lowered = {i.lower(): i for i in options} | {label.lower(): i for i, label in options.items()}
    if text.lower() in lowered:
        notes.append(f"{kind} {text!r} read as {lowered[text.lower()]!r}")
        return lowered[text.lower()]
    close = sorted({lowered[c] for c in difflib.get_close_matches(text.lower(), list(lowered), n=3, cutoff=0.8)})
    if len(close) == 1:
        notes.append(f"{kind} {text!r} read as {close[0]!r}")
        return close[0]
    suggestions = sorted({lowered[c] for c in difflib.get_close_matches(text.lower(), list(lowered), n=3, cutoff=0.5)})
    questions.append(f"which {kind} is {text!r}? " + (f"close matches: {suggestions}" if suggestions else f"known: {sorted(options)}"))
    return None


def resolve(model: SemanticModel, proposal: Mapping[str, Any]) -> Resolution:
    """Ambiguity becomes a question, never a guess. A proposal that resolves is validated like any request."""
    notes: list[str] = []
    questions: list[str] = []
    kpis = {k.name: k.label or k.name for k in model.kpis}
    dims = {d.name: d.label or d.name for d in model.dimensions}
    data = dict(proposal)
    for key, options, kind in (("kpis", kpis, "KPI"), ("rows", dims, "dimension"), ("cols", dims, "dimension")):
        if key in data:
            data[key] = [r for r in (_resolve_name(x, options, kind, notes, questions) for x in data[key] or []) if r is not None]
    if questions:
        return Resolution(None, questions, notes)
    try:
        request = ReportRequest.from_dict(data)
        validate(model, request)
    except RequestError as error:
        return Resolution(None, [f"{error.code}: {error.message}"], notes)
    return Resolution(request, [], notes)
