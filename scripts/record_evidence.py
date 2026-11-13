"""Record what ran, where, and what it returned: the evidence file of specs/library/13-verification-evidence.md.

Runs the request matrix of tests/conftest.py through every available backend/engine pair, compares each result with the
independent reference, and writes a JSON record (versions, warehouse name and size, statement count, per-request outcome; never a host, a user or an id).

    python scripts/record_evidence.py                  # local pairs only
    python scripts/record_evidence.py --databricks     # also the warehouse (EDGEKPI_DBX_WAREHOUSE, DATABRICKS_CONFIG_PROFILE)
"""
from __future__ import annotations

import datetime
import json
import pathlib
import platform
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import duckdb  # noqa: E402
import sqlglot  # noqa: E402
from conftest import DATA, MODEL_PATH, REQUESTS  # noqa: E402

import edgekpi  # noqa: E402
from edgekpi import GeneratedSql, load  # noqa: E402
from edgekpi.backends.malloy import Malloy  # noqa: E402
from edgekpi.backends.metric_view import MetricView  # noqa: E402
from edgekpi.conformance import conformance  # noqa: E402
from edgekpi.engines import malloy as malloy_engine  # noqa: E402
from edgekpi.engines.sql import DatabricksEngine, DuckDBEngine  # noqa: E402

OUT = ROOT / "specs" / "library" / "evidence"


def main() -> int:
    use_databricks = "--databricks" in sys.argv
    model = load(MODEL_PATH)
    duck = DuckDBEngine()
    duck.load(DATA)
    cases = [("sql on duckdb", GeneratedSql(), duck)]
    record: dict = {
        "date": datetime.date.today().isoformat(),
        "versions": {"python": platform.python_version(), "edgekpi": edgekpi.__version__, "sqlglot": sqlglot.__version__, "duckdb": duckdb.__version__},
        "model": {"name": model.name, "fingerprint": model.fingerprint()},
        "requests": list(REQUESTS),
    }
    malloy = None
    if malloy_engine.available():
        malloy = malloy_engine.MalloyDuckDBEngine(DATA)
        cases.append(("malloy on duckdb", Malloy(), malloy))
    warehouse = None
    if use_databricks:
        warehouse = DatabricksEngine()
        warehouse.load(DATA)
        info = warehouse.client.warehouses.get(warehouse.warehouse)
        record["databricks"] = {
            "warehouse": {"name": info.name, "size": info.cluster_size},     # no host, user or id: the record is published
            "schema": f"{warehouse.catalog}.{warehouse.schema}", "tables_created_or_replaced": ["client", "message", "message_event"],
        }
        malloy_on_databricks = malloy_engine.MalloyDatabricksEngine(warehouse) if malloy_engine.available() else None
        cases += [("sql on databricks", GeneratedSql(), warehouse), ("metric view on databricks", MetricView(warehouse.catalog, warehouse.schema), warehouse)]
        if malloy_on_databricks is not None:
            cases.append(("malloy on databricks", Malloy(table_prefix=malloy_on_databricks.table_prefix), malloy_on_databricks))
    results: dict = {}
    failed = 0
    for name, request in REQUESTS.items():
        outcomes = conformance(model, request, cases, duck)
        results[name] = {o.label: {"nodes": o.nodes, "diffs": len(o.diffs), "violations": len(o.violations), "error": o.error} for o in outcomes}
        failed += sum(not o.ok for o in outcomes)
        print(f"{name:30}", " ".join(f"{o.label}={'ok' if o.ok else 'FAIL'}" for o in outcomes))
    record["results"] = results
    record["pairs"] = [c[0] for c in cases]
    record["comparisons"] = len(REQUESTS) * len(cases)
    record["failed"] = failed
    if malloy is not None and malloy.malloy_version:
        record["versions"]["malloy"] = malloy.malloy_version
    if warehouse is not None:
        record["databricks"]["statements_executed"] = warehouse.statements
        record["databricks"]["malloy_connection"] = {"package": "@malloydata/db-databricks 0.0.437",
                                                     "note": "statements run by Malloy through its own connection are not counted in statements_executed"}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"run-{record['date']}{'-databricks' if use_databricks else '-local'}.json"
    path.write_text(json.dumps(record, indent=2, default=str) + "\n")
    print(f"{record['comparisons']} comparisons, {failed} failed; wrote {path.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
