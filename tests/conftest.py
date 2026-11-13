"""Shared fixtures. One model, one data script, one set of engines: every test file reuses them (DRY)."""
from __future__ import annotations

import os
import pathlib

import pytest

from edgekpi import GeneratedSql, load
from edgekpi.backends.malloy import Malloy
from edgekpi.backends.metric_view import MetricView
from edgekpi.engines import malloy as malloy_engine
from edgekpi.engines.sql import DatabricksEngine, DuckDBEngine

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "examples" / "registry" / "model.yaml"
EXAMPLES = ROOT / "examples" / "registry"      # single source of the registry data and templates
DATA = (EXAMPLES / "data.sql").read_text()
HAS_DATABRICKS = bool(os.environ.get("EDGEKPI_DBX_WAREHOUSE") and os.environ.get("DATABRICKS_CONFIG_PROFILE"))

ALL_KPIS = ["sent", "reached", "delivery_rate", "open_rate", "click_rate", "ctor"]

# The request matrix every backend must answer identically (docs: 11-test-strategy, e2e).
REQUESTS = {
    "pivot-with-params-and-where": {"kpis": ALL_KPIS, "rows": ["typology"], "cols": ["market"], "params": {"start_date": "2025-06-01", "end_date": "2026-08-01"}, "where": [{"dim": "market", "in": ["HK", "SG"]}]},
    "grand-total-only": {"kpis": ["sent", "delivery_rate"]},
    "two-row-levels": {"kpis": ALL_KPIS, "rows": ["typology", "tier"], "cols": ["market"]},
    "year-function-no-params": {"kpis": ["sent", "ctor"], "rows": ["send_year"], "cols": ["market"]},
    "totals-off": {"kpis": ["sent", "reached"], "rows": ["typology"], "cols": ["market"], "totals": {"rows": False, "cols": False}},
    "empty-input": {"kpis": ["sent", "delivery_rate"], "rows": ["market"], "where": [{"dim": "market", "in": ["XX"]}]},
    "where-eq-off-axis": {"kpis": ["sent", "click_rate"], "rows": ["typology"], "where": [{"dim": "tier", "eq": "Gold"}]},
    "end-date-only": {"kpis": ["sent", "delivery_rate"], "rows": ["market"], "params": {"end_date": "2025-12-31"}},
    "zero-denominator-group": {"kpis": ["delivery_rate", "open_rate", "ctor"], "rows": ["market"], "where": [{"dim": "market", "in": ["JP", "HK"]}]},
}

PAIRS = [
    "sql-duckdb",
    pytest.param("malloy-duckdb", marks=pytest.mark.malloy),
    pytest.param("sql-databricks", marks=pytest.mark.databricks),
    pytest.param("metric-view-databricks", marks=pytest.mark.databricks),
    pytest.param("malloy-databricks", marks=[pytest.mark.databricks, pytest.mark.malloy]),
]
# name -> (backend factory taking the engine, engine fixture)
_PAIR_PARTS = {
    "sql-duckdb": (lambda engine: GeneratedSql(), "duck"),
    "malloy-duckdb": (lambda engine: Malloy(), "malloy"),
    "sql-databricks": (lambda engine: GeneratedSql(), "databricks"),
    "metric-view-databricks": (lambda engine: MetricView(), "databricks"),
    "malloy-databricks": (lambda engine: Malloy(table_prefix=engine.table_prefix), "malloy_databricks"),
}


@pytest.fixture(scope="session")
def model():
    return load(MODEL_PATH)


@pytest.fixture(scope="session")
def duck():
    engine = DuckDBEngine()
    engine.load(DATA)
    return engine


@pytest.fixture(scope="session")
def malloy():
    if not malloy_engine.available():
        pytest.skip("Malloy runtime not installed: npm install in edgekpi/backends/malloy_runtime")
    return malloy_engine.MalloyDuckDBEngine(DATA)


@pytest.fixture(scope="session")
def databricks():
    if not HAS_DATABRICKS:
        pytest.skip("set DATABRICKS_CONFIG_PROFILE and EDGEKPI_DBX_WAREHOUSE to run on a warehouse")
    engine = DatabricksEngine()
    engine.load(DATA)
    return engine


@pytest.fixture(scope="session")
def malloy_databricks(databricks):
    if not malloy_engine.available():
        pytest.skip("Malloy runtime not installed: npm install in edgekpi/backends/malloy_runtime")
    return malloy_engine.MalloyDatabricksEngine(databricks)


@pytest.fixture
def pair(request):
    """(name, backend, engine) for each backend/engine pair; a missing runtime skips only its own cases."""
    factory, engine_fixture = _PAIR_PARTS[request.param]
    engine = request.getfixturevalue(engine_fixture)
    return request.param, factory(engine), engine
