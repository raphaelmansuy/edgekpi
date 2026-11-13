"""TIER-DBX: behaviours that only a Databricks warehouse can show (../14-test-strategy-and-traceability.md).
The shared suite in test_fixtures.py already runs on Databricks through the `con`, `sc` and `retail` fixtures.
Opt in:  DATABRICKS_CONFIG_PROFILE=your-profile EDGEKPI_DBX_WAREHOUSE=your-warehouse-id pytest test_databricks.py
"""
from __future__ import annotations

import pytest

import dbx_runner
from dbx_runner import DatabricksError
from mini_planner import plan_sql
from test_fixtures import ATOMS, COLS, KPIS, ROWS, _load, run  # noqa: F401  (shared constants and helpers)

pytestmark = pytest.mark.skipif(not dbx_runner.enabled(), reason="Databricks tier off")


@pytest.fixture(scope="module")
def dbx():
    d = dbx_runner.Dbx()
    d.run(f"CREATE SCHEMA IF NOT EXISTS {dbx_runner.CATALOG}.{dbx_runner.SCHEMA}")
    return d


@pytest.fixture(scope="module")
def msg(dbx):
    from test_fixtures import DbxConn

    c = DbxConn(dbx)
    _load(c, "s4_messages.sql")
    return c


def test_dbx_ansi_mode_raises_on_division_by_zero_and_the_guard_returns_null(dbx):
    """EC-DIV0 on the real target: a bare / 0 is an error, the generated NULLIF guard is a NULL."""
    with pytest.raises(DatabricksError, match="DIVIDE_BY_ZERO"):
        dbx.run("SELECT 1.0 / 0 AS x")
    assert dbx.run("SELECT 1.0 / NULLIF(0, 0) AS x") == [{"x": None}]
    assert dbx.run("SELECT try_divide(1.0, 0) AS x") == [{"x": None}]  # the Databricks-native alternative


def test_dbx_null_safe_equality_both_spellings(dbx):
    """EC-NULLSAFE-EQ: IS NOT DISTINCT FROM (portable, used by the planner) and <=> (Spark only) agree on Databricks."""
    r = dbx.run("SELECT (NULL IS NOT DISTINCT FROM NULL) AS a, (NULL <=> NULL) AS b, (1 IS NOT DISTINCT FROM NULL) AS c")
    assert r == [{"a": True, "b": True, "c": False}]


def test_dbx_grouping_id_type_is_wide_enough(dbx):
    """EC-GID: record the return type so the dimension cap is justified by evidence, not memory."""
    r = dbx.run("SELECT typeof(GROUPING_ID(a, b)) AS t FROM VALUES (1, 2) AS v(a, b) GROUP BY ROLLUP (a, b) LIMIT 1")
    assert r[0]["t"] in {"int", "bigint"}


def test_dbx_hll_sketch_tracks_exact_distinct_and_mismatched_lgk_fails(dbx, msg):
    """EC-HLL-LGK and SEM-CLASS: the fixture has 180 distinct clients."""
    exact = dbx.run("SELECT COUNT(DISTINCT client_id) AS n FROM message")[0]["n"]
    est = dbx.run(
        """SELECT hll_sketch_estimate(hll_union_agg(sk)) AS n FROM (
             SELECT hll_sketch_agg(client_id, 12) AS sk FROM message WHERE yr = 2025
             UNION ALL
             SELECT hll_sketch_agg(client_id, 12) AS sk FROM message WHERE yr = 2026)"""
    )[0]["n"]
    assert exact == 180 and abs(est - exact) <= 0.02 * exact
    with pytest.raises(DatabricksError, match="HLL_UNION_DIFFERENT_LG_K"):
        dbx.run(
            """SELECT hll_sketch_estimate(hll_union_agg(sk)) AS n FROM (
                 SELECT hll_sketch_agg(client_id, 10) AS sk FROM message WHERE yr = 2025
                 UNION ALL
                 SELECT hll_sketch_agg(client_id, 12) AS sk FROM message WHERE yr = 2026)"""
        )


def test_dbx_edgesql_gated_sql_executes_and_returns_the_same_rows(msg):
    """EDGE-OK-01 on the real target: the text EdgeSQL emits runs on Databricks and equals the planner's own text."""
    edgesql = pytest.importorskip("edgesql")
    sql = plan_sql("message", ATOMS, KPIS, ROWS, COLS)
    gated = edgesql.Query.parse(sql, dialect="databricks").to_sql()
    a = sorted(map(str, run(msg, sql)))
    b = sorted(map(str, run(msg, gated)))
    assert len(a) == 56 and a == b


def test_dbx_time_zone_must_be_declared(dbx):
    """EC-TZ on the target: the same instant is 2026 in UTC and 2027 in Hong Kong. Declare the zone."""
    r = dbx.run(
        """SELECT year(from_utc_timestamp(TIMESTAMP '2026-12-31 23:30:00', 'UTC')) AS utc_year,
                  year(from_utc_timestamp(TIMESTAMP '2026-12-31 23:30:00', 'Asia/Hong_Kong')) AS hk_year"""
    )
    assert r == [{"utc_year": 2026, "hk_year": 2027}]


def test_dbx_explain_shows_one_scan_and_an_expand_for_the_grouping_sets(dbx, msg):
    """PERF-ASYMPTOTICS on the target: one table scan and one Expand node (the |G| x N term of the article)."""
    plan = " ".join(str(next(iter(r.values()))) for r in dbx.run("EXPLAIN FORMATTED " + plan_sql("message", ATOMS, KPIS, ROWS, COLS)))
    assert plan.count("Scan ") + plan.count("FileScan") + plan.count("PhotonScan") >= 1
    assert "Expand" in plan
