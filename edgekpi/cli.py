"""Command line: validate a model, compile a report to any backend, run it, verify the backends against each other."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from . import loader
from .backends.base import Backend
from .backends.malloy import Malloy
from .backends.metric_view import MetricView
from .backends.sql import GeneratedSql
from .conformance import conformance
from .errors import KpiError
from .estimate import estimate
from .grain import check_grain
from .inference import infer, parse_templates
from .render import pivot_text
from .request import ReportRequest, validate
from .runner import run

BACKENDS = {"sql": GeneratedSql, "metric-view": MetricView, "malloy": Malloy}


def _backend(name: str, args) -> Backend:
    if name == "metric-view":
        return MetricView(args.catalog, args.schema)
    if name == "malloy" and args.databricks:
        return Malloy(table_prefix=f"{args.catalog}.{args.schema}.")
    return BACKENDS[name]()


def _request(path: str) -> ReportRequest:
    return ReportRequest.from_dict(json.loads(pathlib.Path(path).read_text()))


def _duckdb(data: str):
    from .engines.sql import DuckDBEngine

    engine = DuckDBEngine()
    engine.load(pathlib.Path(data).read_text())
    return engine


def _engine_for(backend: str, data: str, args):
    if backend == "malloy":
        from .engines.malloy import MalloyDatabricksEngine, MalloyDuckDBEngine
        if args.databricks:
            return MalloyDatabricksEngine(_warehouse(data, args))
        return MalloyDuckDBEngine(pathlib.Path(data).read_text())
    if args.databricks:
        return _warehouse(data, args)
    return _duckdb(data)


def _warehouse(data: str, args):
    from .engines.sql import DatabricksEngine

    engine = DatabricksEngine(catalog=args.catalog, schema=args.schema)
    engine.load(pathlib.Path(data).read_text())
    return engine


def cmd_validate(args) -> int:
    model = loader.load(args.model)
    print(f"model {model.name} v{model.version} [{model.fingerprint()}] over {model.source} (key {model.key})")
    print("  joins      :", ", ".join(f"{j.name}->{j.table}" for j in model.joins) or "-")
    print("  dimensions :", ", ".join(d.name for d in model.dimensions) or "-")
    print("  measures   :", ", ".join(f"{m.name}[{m.kind}]" for m in model.measures))
    print("  kpis       :", ", ".join(f"{k.name}[{k.status}]" for k in model.kpis) or "-")
    print("  filters    :", ", ".join(f"{f.name}{'?' if f.optional else ''}" for f in model.filters) or "-")
    return 0


def cmd_compile(args) -> int:
    model = loader.load(args.model)
    report = validate(model, _request(args.request))
    plan = _backend(args.backend, args).compile(report)
    for statement in plan.statements:
        print(f"-- {plan.backend} {statement.kind} ({statement.language})")
        print(statement.text, end="\n\n")
    print("--", estimate(report).description)
    return 0


def cmd_run(args) -> int:
    model = loader.load(args.model)
    backend = _backend(args.backend, args)
    result = run(model, _request(args.request), backend, _engine_for(args.backend, args.data, args), reconcile="flag")
    for kpi in result.report.kpis:
        print(pivot_text(result.report, result.grid, kpi.name), end="\n\n")
    print("states:", " > ".join(result.states))
    print("reconciliation:", "all checks pass" if not result.violations else f"{len(result.violations)} violation(s): {result.violations[0].message}")
    return 0 if not result.violations else 1


def cmd_verify(args) -> int:
    from .engines import malloy as malloy_engine

    model = loader.load(args.model)
    duck = _duckdb(args.data)
    cases = [("sql on duckdb", GeneratedSql(), duck)]
    if malloy_engine.available():
        cases.append(("malloy on duckdb", Malloy(), malloy_engine.MalloyDuckDBEngine(pathlib.Path(args.data).read_text())))
    if args.databricks:
        warehouse = _warehouse(args.data, args)
        cases += [("sql on databricks", GeneratedSql(), warehouse), ("metric view on databricks", MetricView(args.catalog, args.schema), warehouse)]
        if malloy_engine.available():
            cases.append(("malloy on databricks", Malloy(table_prefix=f"{args.catalog}.{args.schema}."), malloy_engine.MalloyDatabricksEngine(warehouse)))
    failed = 0
    for outcome in conformance(model, _request(args.request), cases, duck):
        failed += not outcome.ok
        detail = outcome.error or f"{len(outcome.diffs)} diffs, {len(outcome.violations)} violations"
        print(f"{outcome.label:28} {'match' if outcome.ok else 'DIFFER':7} {outcome.nodes} nodes  {detail}")
    return 1 if failed else 0


def cmd_infer(args) -> int:
    engine = _duckdb(args.data) if args.data else None
    dims = dict(item.split("=", 1) for item in args.dim)
    result = infer(parse_templates(pathlib.Path(args.templates).read_text()), name=args.name, key=args.key, dimensions=dims, engine=engine)
    print(loader.dumps(result.model))
    print(f"# accepted {len(result.accepted)}, refused {len(result.refused)}")
    for kpi_id, reason in result.refused.items():
        print(f"# refused {kpi_id}: {reason}")
    for note in result.notes:
        print(f"# note: {note}")
    return 0


def cmd_check_grain(args) -> int:
    print(check_grain(_duckdb(args.data), loader.load(args.model)))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="edgekpi", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p, request=False, data=False, backend=False):
        p.add_argument("model")
        if request:
            p.add_argument("request")
        if data:
            p.add_argument("--data", required=True, help="SQL script that creates the tables")
        if backend:
            p.add_argument("--backend", choices=sorted(BACKENDS), default="sql")
        p.add_argument("--databricks", action="store_true", help="run on the warehouse named by EDGEKPI_DBX_WAREHOUSE")
        p.add_argument("--catalog", default="workspace")
        p.add_argument("--schema", default="edgekpi_lib")

    common(sub.add_parser("validate", help="check a model file"))
    common(sub.add_parser("compile", help="show the statements a backend produces"), request=True, backend=True)
    common(sub.add_parser("run", help="run a report and print it"), request=True, data=True, backend=True)
    common(sub.add_parser("verify", help="compare every backend with the independent reference"), request=True, data=True)
    common(sub.add_parser("check-grain", help="check key uniqueness and join fan-out"), data=True)
    p = sub.add_parser("infer", help="infer a model from registry templates")
    p.add_argument("templates")
    p.add_argument("--name", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--dim", action="append", default=[], metavar="NAME=EXPR")
    p.add_argument("--data")
    args = parser.parse_args(argv)
    handlers = {"validate": cmd_validate, "compile": cmd_compile, "run": cmd_run, "verify": cmd_verify, "infer": cmd_infer, "check-grain": cmd_check_grain}
    try:
        return handlers[args.command](args)
    except KpiError as error:
        print(f"{error.code}: {error.message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
