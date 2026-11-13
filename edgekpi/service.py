"""A service layer: the calls a host or a user interface needs, as functions from JSON-shaped input to JSON-shaped output.

It holds a model, the data it runs on and the engines. It maps every library error to a payload with a stable code, so a
client branches on `error.code` and never parses a message. The HTTP wrapper in `server.py` adds nothing but routing.
"""
from __future__ import annotations

import json
import pathlib
import threading
from dataclasses import asdict
from typing import Any, Mapping

from . import loader
from .backends.base import Backend, Engine, Statement
from .backends.malloy import Malloy
from .backends.metric_view import MetricView
from .backends.sql import GeneratedSql
from .conformance import conformance
from .errors import DefinitionError, EngineError, KpiError, RequestError, UnsupportedError
from .estimate import estimate
from .explain import explain
from .grain import check_grain
from .inference import infer, parse_templates
from .intent import catalog, request_json_schema, resolve
from .parity import verify as verify_parity
from .request import ReportRequest, validate
from .runner import run

STATUS_BY_ERROR = ((RequestError, 422), (DefinitionError, 422), (UnsupportedError, 501), (EngineError, 502), (KpiError, 422))


def error_payload(error: Exception) -> tuple[int, dict[str, Any]]:
    if isinstance(error, KpiError):
        status = next(code for kind, code in STATUS_BY_ERROR if isinstance(error, kind))
        return status, {"ok": False, "error": {"code": error.code, "message": error.message, "states": error.detail.get("states", [])}}
    return 500, {"ok": False, "error": {"code": "INTERNAL", "message": type(error).__name__, "states": []}}


DEFAULT_TABLE_PREFIX = "workspace.edgekpi_lib."

# What Malloy needs to reach each engine. Values in angle brackets are placeholders; the token is read from the environment.
MALLOY_CONNECTIONS = {
    "duckdb": "new DuckDBConnection('duckdb', ':memory:')\n// the example tables are created in memory first",
    "databricks": (
        "new DatabricksConnection('databricks', {\n"
        "  host: '<workspace-host>',\n"
        "  path: '/sql/1.0/warehouses/<warehouse-id>',\n"
        "  token: process.env.EDGEKPI_DBX_TOKEN,   // never written in the model\n"
        "  defaultCatalog: '<catalog>',\n"
        "  defaultSchema: '<schema>',\n"
        "})"
    ),
}


class Service:
    def __init__(
        self, model_path: str | pathlib.Path, data_path: str | pathlib.Path, templates_path: str | pathlib.Path | None = None,
        evidence_path: str | pathlib.Path | None = None, legacy_dimensions: Mapping[str, str] | None = None, warehouse=None,
    ):
        from .engines import malloy as malloy_engine
        from .engines.sql import DuckDBEngine

        self.model = loader.load(model_path)
        self.data = pathlib.Path(data_path).read_text()
        self.templates_path = pathlib.Path(templates_path) if templates_path else None
        self.evidence_path = pathlib.Path(evidence_path) if evidence_path else None
        self.legacy_dimensions = dict(legacy_dimensions or {})
        self.lock = threading.Lock()            # one DuckDB connection is shared; calls are serialised
        self.duck = DuckDBEngine()
        self.duck.load(self.data)
        self.warehouse = warehouse
        self._inference: dict[str, Any] | None = None
        self.backends: dict[str, tuple[Backend, Engine | None, str]] = {
            "sql": (GeneratedSql(), self.duck, "DuckDB"),
            "malloy": (Malloy(), malloy_engine.MalloyDuckDBEngine(self.data) if malloy_engine.available() else None, "Malloy on DuckDB"),
            "metric-view": (MetricView(), warehouse, "Databricks warehouse"),
        }

    # ---- reading ------------------------------------------------------------------------------------------------
    def backend_status(self) -> list[dict[str, Any]]:
        reasons = {"malloy": "needs node and `npm install` in edgekpi/backends/malloy_runtime", "metric-view": "needs a Databricks SQL warehouse; not connected in this demo"}
        return [{"id": name, "label": label, "available": engine is not None, "reason": None if engine is not None else reasons.get(name, "unavailable")}
                for name, (_, engine, label) in self.backends.items()]

    def catalogue(self) -> dict[str, Any]:
        m = self.model
        with self.lock:
            grain = check_grain(self.duck, m)
            members = {d.name: self._members(d.name) for d in m.dimensions}
        return {
            "ok": True, **catalog(m), "source": m.source, "key": m.key, "grain": grain,
            "joins": [{"id": j.name, "table": j.table, "on": j.on} for j in m.joins],
            "dimensions": [{"id": d.name, "label": d.label or d.name, "expr": d.expr, "members": members[d.name]} for d in m.dimensions],
            "measures": [{"id": x.name, "expr": x.expr, "kind": x.kind, "additive": x.additive} for x in m.measures],
            "kpis": [{"id": k.name, "label": k.label or k.name, "formula": k.formula, "status": k.status, "owner": k.owner, "format": k.format, "measures": k.refs} for k in m.kpis],
            "filters": [{"id": f.name, "predicate": f.predicate, "optional": f.optional, "params": {p.name: p.type for p in f.params}} for f in m.filters],
            "backends": self.backend_status(), "schema": request_json_schema(m),
        }

    def _members(self, dimension: str) -> list[Any]:
        """The members a dimension takes in the data, for a filter picker. NULL sorts last."""
        request = {"kpis": [self.model.kpis[0].name], "rows": [dimension], "totals": {"rows": False}}
        grid = run(self.model, request, GeneratedSql(), self.duck, reconcile="off").grid
        return sorted((n.members[0] for n in grid.cells), key=lambda v: (v is None, str(v)))

    def messages(self) -> dict[str, Any]:
        """The raw rows behind every report, for the tutorial: one row per message, with its client's typology."""
        text = (
            "SELECT m.message_id, m.client_id, c.typology, m.market, CAST(m.send_date AS VARCHAR) AS send_date, "
            "m.is_delivered, m.is_opened, m.is_clicked FROM message m LEFT JOIN client c ON m.client_id = c.client_id ORDER BY m.message_id"
        )
        with self.lock:
            rows = self.duck.execute(Statement(text))
        return {"ok": True, "rows": rows}

    def evidence(self) -> dict[str, Any]:
        if self.evidence_path is None or not self.evidence_path.exists():
            return {"ok": True, "available": False}
        data = json.loads(self.evidence_path.read_text())
        return {"ok": True, "available": True, "date": data["date"], "pairs": data["pairs"], "comparisons": data["comparisons"], "failed": data["failed"],
                "versions": data["versions"], "requests": data["requests"], "results": data["results"],
                "warehouse": data.get("databricks", {}).get("warehouse"), "statements": data.get("databricks", {}).get("statements_executed")}

    # ---- the report ---------------------------------------------------------------------------------------------
    def _pick(self, backend: str):
        if backend not in self.backends:
            raise RequestError("REQ_UNKNOWN_BACKEND", f"unknown backend {backend!r}; known: {sorted(self.backends)}")
        chosen, engine, _ = self.backends[backend]
        if engine is None:
            reason = next(s["reason"] for s in self.backend_status() if s["id"] == backend)
            raise UnsupportedError("ENGINE_UNAVAILABLE", f"backend {backend} is not available here: {reason}")
        return chosen, engine

    def _malloy_for(self, engine: str | None) -> tuple[Malloy, dict[str, str]]:
        """The Malloy translator for one engine, and the connection that engine needs (placeholders, never a secret)."""
        engine = engine or "duckdb"
        if engine == "duckdb":
            return self.backends["malloy"][0], {"engine": "duckdb", "label": "DuckDB", "language": "javascript", "text": MALLOY_CONNECTIONS["duckdb"]}
        if engine == "databricks":
            return Malloy("databricks", table_prefix=self._warehouse_prefix()), {"engine": "databricks", "label": "Databricks", "language": "javascript", "text": MALLOY_CONNECTIONS["databricks"]}
        raise RequestError("REQ_UNKNOWN_ENGINE", f"unknown Malloy engine {engine!r}; known: ['databricks', 'duckdb']")

    def _warehouse_prefix(self) -> str:
        """`catalog.schema.` where the recorded warehouse run put its tables; a stated default when no run is recorded."""
        if self.evidence_path is not None and self.evidence_path.exists():
            schema = json.loads(self.evidence_path.read_text()).get("databricks", {}).get("schema")
            if schema:
                return f"{schema}."
        return DEFAULT_TABLE_PREFIX

    def plan(self, request: Mapping[str, Any], backend: str = "sql", engine: str | None = None) -> dict[str, Any]:
        report = validate(self.model, ReportRequest.from_dict(request))
        if engine is not None and backend != "malloy":
            raise RequestError("REQ_ENGINE_NOT_APPLICABLE", f"an engine is chosen only for Malloy, not for {backend!r}")
        connection = None
        if backend == "malloy":
            chosen, connection = self._malloy_for(engine)
        else:
            chosen = self.backends[backend][0] if backend in self.backends else self._pick(backend)[0]
        plan = chosen.compile(report)
        return {
            "ok": True, "backend": backend, "connection": connection, "notes": list(plan.notes), "estimate": asdict(estimate(report)) | {"description": estimate(report).description},
            "statements": [{"kind": s.kind, "language": s.language, "text": s.text} for s in plan.statements],
            "bindings": [{"name": b.name, "value": b.value, "type": b.type} for b in plan.query.params if b.value is not None],
            "scopes": [list(s) for s in report.scopes],
        }

    def run(self, request: Mapping[str, Any], backend: str = "sql") -> dict[str, Any]:
        chosen, engine = self._pick(backend)
        with self.lock:
            result = run(self.model, request, chosen, engine, reconcile="flag")
        report, grid = result.report, result.grid
        return {
            "ok": True, "backend": backend, "states": result.states,
            "dims": list(report.dims), "rows": list(report.request.rows), "cols": list(report.request.cols),
            "kpis": [{"id": k.name, "label": k.label or k.name, "format": k.format, "status": k.status, "measures": k.refs} for k in report.kpis],
            "measures": [m.name for m in report.atoms],
            "nodes": [{"scope": list(n.scope), "members": list(n.members), "values": v} for n, v in grid.cells.items()],
            "violations": [{"code": v.code, "node": dict(v.node), "message": v.message} for v in result.violations],
            "scopes": [list(s) for s in report.scopes], "estimate": estimate(report).description,
        }

    def explain(self, request: Mapping[str, Any], kpi: str, scope: list[str], members: list[Any], backend: str = "sql") -> dict[str, Any]:
        chosen, engine = self._pick(backend)
        with self.lock:
            result = run(self.model, request, chosen, engine, reconcile="flag")
        return {"ok": True, **explain(result.report, result.grid, kpi, tuple(scope), tuple(members))}

    def verify(self, request: Mapping[str, Any]) -> dict[str, Any]:
        cases = [(label, backend, engine) for backend, engine, label in self.backends.values() if engine is not None]
        parsed = ReportRequest.from_dict(request)
        with self.lock:
            outcomes = conformance(self.model, parsed, cases, self.duck)
        return {"ok": True, "outcomes": [{"label": o.label, "ok": o.ok, "nodes": o.nodes, "diffs": len(o.diffs), "violations": len(o.violations), "error": o.error} for o in outcomes],
                "skipped": [s for s in self.backend_status() if not s["available"]]}

    def resolve(self, proposal: Mapping[str, Any]) -> dict[str, Any]:
        r = resolve(self.model, proposal)
        return {"ok": True, "request": None if r.request is None else {
            "kpis": list(r.request.kpis), "rows": list(r.request.rows), "cols": list(r.request.cols),
            "totals": {"rows": r.request.row_totals, "cols": r.request.col_totals}, "params": dict(r.request.params)},
            "questions": r.questions, "notes": r.notes}

    # ---- migration ----------------------------------------------------------------------------------------------
    def inference(self) -> dict[str, Any]:
        if self.templates_path is None:
            return {"ok": True, "available": False}
        if self._inference is None:
            templates = parse_templates(self.templates_path.read_text())
            with self.lock:
                result = infer(templates, name="registry", key=self.model.key, dimensions={d.name: d.expr for d in self.model.dimensions if d.name in self.legacy_dimensions}, engine=self.duck)
                bindings = [{"start_date": None, "end_date": None}, {"start_date": "2026-01-01", "end_date": None}, {"start_date": "2025-06-01", "end_date": "2026-03-01"}]
                parity = verify_parity(self.duck, templates, result, rows=("typology",), cols=("market",), legacy_dimensions=self.legacy_dimensions, bindings=bindings)
            by_id = {t.kpi_id: t for t in templates}
            self._inference = {
                "ok": True, "available": True,
                "templates": [{"id": t.kpi_id, "alias": t.alias, "sql": t.sql, "accepted": t.kpi_id in result.accepted, "kpi": result.accepted.get(t.kpi_id), "reason": result.refused.get(t.kpi_id)} for t in templates],
                "measures": [{"id": m.name, "expr": m.expr, "kind": m.kind} for m in result.model.measures],
                "kpis": [{"id": k.name, "formula": k.formula, "status": k.status, "legacy": by_id[next(i for i, a in result.accepted.items() if a == k.name)].sql} for k in result.model.kpis],
                "filters": [{"id": f.name, "predicate": f.predicate, "optional": f.optional, "params": {p.name: p.type for p in f.params}} for f in result.model.filters],
                "grain": result.grain, "notes": result.notes,
                "parity": {"bindings": parity.bindings, "nodes": parity.nodes, "compared": parity.compared, "nulls": parity.null_values, "different": len(parity.different), "only_after": len(parity.only_after)},
                "yaml": loader.dumps(result.model),
            }
        return self._inference
