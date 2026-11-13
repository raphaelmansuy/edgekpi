"""Executable evidence for the KPI specification set.

Run:  uv run --with duckdb --with pytest pytest specs/kpi/fixtures -q
Every number quoted in ../0x-*.md that is not copied from the article comes from here.
Test ids are referenced by the specs as CASE-* (see ../14-test-strategy-and-traceability.md).
"""

from __future__ import annotations

import pathlib
import re

import duckdb
import pytest

import dbx_runner
from mini_planner import MAX_DIMS, Atom, Kpi, Part, drill_across_sql, grouping_sets, oracle_sql, plan_sql

HERE = pathlib.Path(__file__).parent

ATOMS = [
    Atom("sent", "COUNT(*)"),
    Atom("delivered", "COUNT(*) FILTER (WHERE is_delivered)"),
    Atom("opened", "COUNT(*) FILTER (WHERE is_opened)"),
    Atom("clicked", "COUNT(*) FILTER (WHERE is_clicked)"),
    Atom("clients", "COUNT(DISTINCT client_id)"),
]
KPIS = [
    Kpi.ratio("delivery_rate", "delivered", "sent"),
    Kpi.ratio("open_rate", "opened", "delivered"),
    Kpi.ratio("click_rate", "clicked", "delivered"),
    Kpi.ratio("ctor", "clicked", "opened"),
]
ROWS = ["typology", "tier", "campaign"]
COLS = ["yr", "market"]
ALL_DIMS = ROWS + COLS

# Illustrative synthetic grid (scenario 4). (sent, delivery rate in %) per column.
# Column order: 2025 HK, 2025 SG, 2025 TOTAL, 2026 HK, 2026 SG, 2026 TOTAL, GRAND TOTAL
COLS_KEYS = [(2025, "HK"), (2025, "SG"), (2025, None), (2026, "HK"), (2026, "SG"), (2026, None), (None, None)]
CASE_GRID = {
    ("New", "Gold", "A"): [(100, 80), (50, 90), (150, 83.3), (200, 90), (100, 80), (300, 86.7), (450, 85.6)],
    ("New", "Gold", "B"): [(100, 70), (50, 80), (150, 73.3), (100, 90), (50, 90), (150, 90), (300, 81.7)],
    ("New", "Gold", None): [(200, 75), (100, 85), (300, 78.3), (300, 90), (150, 83.3), (450, 87.8), (750, 84.0)],
    ("Existing", "Silver", "C"): [(50, 80), (100, 70), (150, 73.3), (50, 90), (100, 80), (150, 83.3), (300, 78.3)],
    (None, None, None): [(250, 76), (200, 77.5), (450, 76.7), (350, 90), (250, 82), (600, 86.7), (1050, 82.4)],
}


class DbxConn:
    """Gives a Databricks warehouse the tiny slice of the DuckDB connection API that the tests use, so ONE suite
    checks both adapters (Liskov: same rows, same behaviour). Rows come back as tuples in column order."""

    kind = "databricks"

    def __init__(self, dbx):
        self.dbx, self._rows, self.description = dbx, [], []

    def execute(self, sql):
        rows = self.dbx.run(sql)
        self.description = [(k,) for k in (rows[0].keys() if rows else [])]
        self._rows = [tuple(r.values()) for r in rows]
        return self

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


_DBX = {}


def _dbx_conn():
    if not dbx_runner.enabled():
        pytest.skip("Databricks tier off: set DATABRICKS_CONFIG_PROFILE and EDGEKPI_DBX_WAREHOUSE")
    if "d" not in _DBX:
        _DBX["d"] = dbx_runner.Dbx()
        _DBX["d"].run(f"CREATE SCHEMA IF NOT EXISTS {dbx_runner.CATALOG}.{dbx_runner.SCHEMA}")
    return DbxConn(_DBX["d"])


def _load(c, sql_file):
    if getattr(c, "kind", "") == "databricks":
        c.dbx.script((HERE / sql_file.replace(".sql", "_databricks.sql")).read_text() if sql_file == "s4_messages.sql" else (HERE / sql_file).read_text())
    else:
        c.execute((HERE / sql_file).read_text())
    return c


@pytest.fixture(scope="module", params=["duckdb", "databricks"])
def con(request):
    c = _dbx_conn() if request.param == "databricks" else duckdb.connect()
    return _load(c, "s4_messages.sql")


@pytest.fixture(params=["duckdb", "databricks"])
def sc(request):
    """Scratch connection for edge-case tests. DuckDB: fresh in-memory. Databricks: shared, tables replaced by name."""
    return _dbx_conn() if request.param == "databricks" else duckdb.connect()


def run(con, sql):
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


@pytest.fixture(scope="module")
def grid(con):
    return run(con, plan_sql("message", ATOMS, KPIS, ROWS, COLS))


def pick(grid, typology, tier, campaign, yr, market):
    hits = [
        d
        for d in grid
        if (d["typology"], d["tier"], d["campaign"], d["yr"], d["market"]) == (typology, tier, campaign, yr, market)
    ]
    assert len(hits) == 1, (typology, tier, campaign, yr, market, len(hits))
    return hits[0]


# ----------------------------------------------------------------------------------------------
# CASE-S4-PARITY  The illustrative scenario 4 grid, produced by ONE statement over ONE scan.
# ----------------------------------------------------------------------------------------------
def test_s4_matches_business_case_grid(grid):
    for (typ, tier, camp), expected in CASE_GRID.items():
        for (yr, mkt), (sent, dr) in zip(COLS_KEYS, expected):
            cell = pick(grid, typ, tier, camp, yr, mkt)
            assert cell["sent"] == sent, ((typ, tier, camp), yr, mkt)
            assert round(cell["delivery_rate"] * 100, 1) == dr, ((typ, tier, camp), yr, mkt, cell["delivery_rate"])


def test_s4_is_12_grouping_sets_and_56_rows(grid):
    assert len(grouping_sets(ROWS, COLS)) == 12  # 4 row levels x 3 column levels
    assert len(grid) == 56  # sparse: the three fixture rows only produce the nodes that exist


def test_single_statement_equals_one_query_per_node(con, grid):
    """CASE-ORACLE: the planner output equals the baseline (one GROUP BY per node), node by node."""
    for node in grouping_sets(ROWS, COLS):
        expected = run(con, oracle_sql("message", ATOMS, node))
        expected_by_key = {tuple(r.get(d) for d in ALL_DIMS): r for r in expected}
        for key, exp in expected_by_key.items():
            got = [d for d in grid if tuple(d[x] for x in ALL_DIMS) == key]
            # a NULL member and a subtotal share a key, so disambiguate by the node's own dims
            got = [d for d in got if all((d[x] is None) == (x not in node) for x in ALL_DIMS)]
            assert len(got) == 1, (node, key)
            for a in ATOMS:
                assert got[0][a.name] == exp[a.name], (node, key, a.name)


# ----------------------------------------------------------------------------------------------
# PRB-TOTALS-RATE  A rate total is a ratio of totals, never a mean of rates.
# ----------------------------------------------------------------------------------------------
def test_mean_of_rates_is_wrong(grid):
    grand = pick(grid, None, None, None, None, None)
    campaigns = [pick(grid, t, ti, c, None, None) for t, ti, c in [("New", "Gold", "A"), ("New", "Gold", "B"), ("Existing", "Silver", "C")]]
    mean_of_rates = sum(c["delivery_rate"] for c in campaigns) / len(campaigns)
    assert round(grand["delivery_rate"] * 100, 1) == 82.4
    assert round(mean_of_rates * 100, 1) == 81.9  # what a dashboard that averages displayed rates shows
    assert round(grand["delivery_rate"] * 100, 1) != round(mean_of_rates * 100, 1)


def test_year_total_mean_of_rates_is_wrong(grid):
    y25, y26 = pick(grid, None, None, None, 2025, None), pick(grid, None, None, None, 2026, None)
    grand = pick(grid, None, None, None, None, None)
    assert round((y25["delivery_rate"] + y26["delivery_rate"]) / 2 * 100, 1) == 81.7
    assert round(grand["delivery_rate"] * 100, 1) == 82.4


# ----------------------------------------------------------------------------------------------
# PRB-TOTALS-DISTINCT  Unique clients are not additive across campaigns, years, markets.
# ----------------------------------------------------------------------------------------------
def test_unique_clients_do_not_add_up(grid):
    a = pick(grid, "New", "Gold", "A", None, None)["clients"]
    b = pick(grid, "New", "Gold", "B", None, None)["clients"]
    tier = pick(grid, "New", "Gold", None, None, None)["clients"]
    assert (a, b, tier) == (120, 120, 120)  # both campaigns reached the same 120 clients
    assert a + b == 240  # summing the displayed subtotal children doubles the audience

    y25, y26 = pick(grid, None, None, None, 2025, None)["clients"], pick(grid, None, None, None, 2026, None)["clients"]
    grand = pick(grid, None, None, None, None, None)["clients"]
    assert (y25, y26, grand) == (175, 180, 180)
    assert y25 + y26 == 355  # 175 more than the true audience


def test_cross_kpi_union_is_not_a_sum(con):
    """A combined audience over several client-count KPIs is one distinct count over the union, not a sum."""
    row = run(
        con,
        """SELECT COUNT(DISTINCT client_id) AS sent_clients,
                  COUNT(DISTINCT client_id) FILTER (WHERE is_delivered) AS delivered_clients,
                  COUNT(DISTINCT client_id) FILTER (WHERE is_opened)    AS opened_clients,
                  COUNT(DISTINCT client_id) AS union_clients  -- populations are nested, so the union is the largest set
           FROM message""",
    )[0]
    summed = row["sent_clients"] + row["delivered_clients"] + row["opened_clients"]
    assert row["union_clients"] == row["sent_clients"] == 180
    assert summed > row["union_clients"]


# ----------------------------------------------------------------------------------------------
# PRB-COMPOSE  CTOR is composed from atoms, and composing ratios of ratios is not the same thing.
# ----------------------------------------------------------------------------------------------
def test_ctor_from_atoms_equals_click_rate_over_open_rate(grid):
    for d in grid:
        if d["delivered"] and d["opened"]:
            assert d["ctor"] == pytest.approx(d["click_rate"] / d["open_rate"])


def test_mean_of_cell_ctor_is_not_total_ctor(grid):
    cells = [d for d in grid if d["campaign"] and d["yr"] and d["market"]]
    grand = pick(grid, None, None, None, None, None)
    mean_cells = sum(d["ctor"] for d in cells) / len(cells)
    assert abs(mean_cells - grand["ctor"]) > 1e-5  # small here, large when cell sizes diverge (EC-RATE-WEIGHT)


# ----------------------------------------------------------------------------------------------
# PRB-NAMING  One label, two readings: the same word can name two different denominators.
# ----------------------------------------------------------------------------------------------
def test_a_ctr_label_has_two_readings_that_disagree(grid):
    """'CTR' read as clicks / delivered and as clicks / opened gives different numbers on the same node."""
    grand = pick(grid, None, None, None, None, None)
    assert grand["click_rate"] != pytest.approx(grand["ctor"])
    assert grand["ctor"] == pytest.approx(grand["click_rate"] / grand["open_rate"])


# ----------------------------------------------------------------------------------------------
# PRB-BASELINE  Statement count of a one-query-per-KPI layer versus one pass.
# ----------------------------------------------------------------------------------------------
KPI_ATOMS = {  # the six KPIs of the reporting scenarios and the atoms each one needs (numerator, denominator)
    "message_sent": ["sent"],
    "message_reached": ["clients"],
    "delivery_rate": ["delivered", "sent"],
    "open_rate": ["opened", "delivered"],
    "click_rate": ["clicked", "delivered"],
    "ctor": ["clicked", "opened"],
}
BY_NAME = {a.name: a for a in ATOMS}


def baseline_statements(row_dims, col_dims, correct_totals):
    """Emulate a one-query-per-KPI layer. as-is: one statement per KPI (totals recomputed in the tool, wrong for rates and
    distincts). correct: one statement per KPI per requested node (what a team must do to get the totals right)."""
    nodes = grouping_sets(row_dims, col_dims, correct_totals, correct_totals) if correct_totals else [tuple(row_dims + col_dims)]
    return [oracle_sql("message", [BY_NAME[a] for a in atoms], node) for atoms in KPI_ATOMS.values() for node in nodes]


@pytest.mark.parametrize(
    "scenario,row_dims,col_dims,as_is,correct",
    [("S1", ["typology"], [], 6, 6), ("S2", ROWS, [], 6, 6), ("S3", ROWS, COLS, 6, 6), ("S4", ROWS, COLS, 6, 72)],
)
def test_baseline_statement_count_vs_one_pass(con, scenario, row_dims, col_dims, as_is, correct):
    if getattr(con, "kind", "") == "databricks":
        pytest.skip("the 72 baseline statements are measured in bench_dbx.py")
    assert len(baseline_statements(row_dims, col_dims, False)) == as_is
    stmts = baseline_statements(row_dims, col_dims, scenario == "S4")
    assert len(stmts) == correct
    for s in stmts:  # every emulated statement is valid SQL against the fixture
        con.execute(s).fetchall()
    one_pass = plan_sql("message", ATOMS, KPIS, row_dims, col_dims, row_totals=scenario == "S4", col_totals=scenario == "S4")
    assert one_pass.count("FROM message") == 1  # one scan, one statement, whatever the KPI count


# ----------------------------------------------------------------------------------------------
# EC-*  Edge cases that the specification must mitigate. Each one is a failing naive query first.
# ----------------------------------------------------------------------------------------------
def test_ec_null_member_looks_like_subtotal(sc):
    c = sc
    c.execute("CREATE OR REPLACE TABLE m AS SELECT * FROM (VALUES ('HK', 1), (NULL, 1), ('SG', 1)) t(market, n)")
    naive = run(c, "SELECT market, COUNT(*) AS n FROM m GROUP BY ROLLUP (market) ORDER BY 1")
    assert [r["market"] for r in naive].count(None) == 2  # unknown member and grand total are indistinguishable
    safe = run(c, "SELECT market, GROUPING(market) AS is_total, COUNT(*) AS n FROM m GROUP BY ROLLUP (market)")
    assert sorted((r["market"] is None, r["is_total"]) for r in safe) == [(False, 0), (False, 0), (True, 0), (True, 1)]


def test_ec_empty_cell_ratio_is_null_not_zero(sc):
    """A node with zero denominator must return NULL. Fixture has no 2025/'HK' VIP row, so build one."""
    c = sc
    c.execute("CREATE OR REPLACE TABLE x AS SELECT * FROM (VALUES (2025, 'HK', FALSE), (2025, 'HK', TRUE)) t(yr, market, is_delivered)")
    r = run(c, "SELECT COUNT(*) FILTER (WHERE is_delivered) * 1.0 / NULLIF(COUNT(*) FILTER (WHERE FALSE), 0) AS rate FROM x")
    assert r[0]["rate"] is None


def test_ec_event_fanout_inflates_open_count(sc):
    """Several open events per message: COUNT(*) over the event join counts events, not messages."""
    c = sc
    c.execute("CREATE OR REPLACE TABLE msg AS SELECT * FROM (VALUES (1,'A'),(2,'A'),(3,'B')) t(message_id, campaign)")
    c.execute("CREATE OR REPLACE TABLE ev  AS SELECT * FROM (VALUES (1,'open'),(1,'open'),(1,'open'),(2,'open'),(3,'click')) t(message_id, kind)")
    naive = run(c, "SELECT COUNT(*) AS opened FROM msg m JOIN ev e USING (message_id) WHERE e.kind='open'")[0]["opened"]
    right = run(c, "SELECT COUNT(DISTINCT m.message_id) AS opened FROM msg m JOIN ev e USING (message_id) WHERE e.kind='open'")[0]["opened"]
    assert (naive, right) == (4, 2)


def test_ec_scd2_dimension_duplicates_facts(sc):
    """A client changes tier mid-year: joining the fact to a type-2 dimension without an as-of key duplicates messages."""
    c = sc
    c.execute("CREATE OR REPLACE TABLE msg AS SELECT * FROM (VALUES (1,'C1', DATE '2026-03-01'),(2,'C2', DATE '2026-03-01')) t(message_id, client_id, d)")
    c.execute(
        """CREATE OR REPLACE TABLE client_dim AS SELECT * FROM (VALUES
             ('C1','Silver', DATE '2025-01-01', DATE '2026-01-31'),
             ('C1','Gold',   DATE '2026-02-01', DATE '9999-12-31'),
             ('C2','Gold',   DATE '2025-01-01', DATE '9999-12-31')) t(client_id, tier, valid_from, valid_to)"""
    )
    naive = run(c, "SELECT COUNT(*) AS n FROM msg m JOIN client_dim d USING (client_id)")[0]["n"]
    asof = run(c, "SELECT COUNT(*) AS n FROM msg m JOIN client_dim d ON d.client_id=m.client_id AND m.d BETWEEN d.valid_from AND d.valid_to")[0]["n"]
    assert (naive, asof) == (3, 2)


def test_ec_period_filter_and_year_column_and_prior_year(con):
    """Year is both filtered and a column. Year-over-year needs data OUTSIDE a naive filter."""
    c = con
    naive = run(
        c,
        """SELECT market,
                  COUNT(*) FILTER (WHERE yr = 2026) AS cur,
                  COUNT(*) FILTER (WHERE yr = 2025) AS prior
           FROM message WHERE yr = 2026 GROUP BY market ORDER BY market""",
    )
    assert [r["prior"] for r in naive] == [0, 0]  # the report filter removed the comparison rows
    widened = run(
        c,
        """SELECT market,
                  COUNT(*) FILTER (WHERE yr = 2026) AS cur,
                  COUNT(*) FILTER (WHERE yr = 2025) AS prior
           FROM message WHERE yr IN (2026, 2025) GROUP BY market ORDER BY market""",
    )
    assert [(r["market"], r["cur"], r["prior"]) for r in widened] == [("HK", 350, 250), ("SG", 250, 200)]


def test_ec_single_child_subtotal_duplicates_parent(grid):
    """New has one tier (Gold): the Typology subtotal equals the Typology x Tier subtotal."""
    a = pick(grid, "New", "Gold", None, None, None)
    b = pick(grid, "New", None, None, None, None)
    assert {k: a[k] for k in ("sent", "delivered", "clients")} == {k: b[k] for k in ("sent", "delivered", "clients")}


def test_ec_zero_denominator_in_a_non_empty_node_gives_null_rates_through_the_planner(con):
    """EC-DIV0: rows exist, delivered = 0, so open_rate = opened / delivered is 0 / 0. Must be NULL on every engine.
    Databricks (ANSI mode) raises DIVIDE_BY_ZERO without the generated guard; DuckDB returns inf."""
    out = run(con, plan_sql("message", ATOMS, KPIS, ROWS, COLS, where="typology = 'New' AND NOT is_delivered"))
    assert out and all(d["delivered"] == 0 and d["sent"] > 0 for d in out)
    assert all(d["open_rate"] is None and d["click_rate"] is None and d["ctor"] is None for d in out)
    assert all(d["delivery_rate"] == 0 for d in out)  # 0 / sent is a real zero, not a missing value


def test_ec_empty_input_yields_no_node_rows_on_every_engine(con):
    """EC-EMPTY-TOTAL: GROUP BY GROUPING SETS (..., ()) over zero rows returns a count-0 grand-total row on DuckDB
    (SQL standard reading) and NO row on Databricks. Found by running this suite on both. The planner pins one
    semantics: a node exists only if it has input rows (HAVING COUNT(*) > 0); the assembler fills the rest as no_data."""
    out = run(con, plan_sql("message", ATOMS, KPIS, ROWS, COLS, where="typology = 'VIP'"))
    assert out == []


def test_planner_without_kpi_formulas_is_valid_sql_on_every_engine(con):
    """Found by the Databricks benchmark: no KPI formula left a trailing comma in SELECT. DuckDB accepts it,
    Databricks rejects it (TRAILING_COMMA_IN_SELECT). Atoms-only requests are legitimate (Message Sent is just `sent`)."""
    sql = plan_sql("message", ATOMS, [], ROWS, COLS)
    assert not re.search(r",\s*FROM", sql)
    assert len(run(con, sql)) == 56


def test_ec_unknown_atom_fails_closed():
    with pytest.raises(ValueError):
        plan_sql("message", ATOMS, [Kpi("bad", "{delivered} / {nonexistent}")], ROWS, COLS)


def test_ec_gid_first_column_is_the_highest_bit(grid):
    """EC-GID: gid 0 = finest detail, all ones = grand total, and (typology) alone = everything else rolled up."""
    def gid_of(dims_in_node):
        return sum(1 << (len(ALL_DIMS) - 1 - i) for i, d in enumerate(ALL_DIMS) if d not in dims_in_node)
    assert {d["gid"] for d in grid} == {gid_of(n) for n in grouping_sets(ROWS, COLS)}
    assert gid_of(()) == 31 and gid_of(tuple(ALL_DIMS)) == 0 and gid_of(("typology",)) == 15
    for d in grid:  # every row's NULL pattern matches its gid bits
        assert gid_of(tuple(x for x in ALL_DIMS if d[x] is not None)) == d["gid"]


def test_ec_time_zone_decides_the_year():
    """EC-TZ: 23:30 UTC on 31 Dec is already 1 Jan in Hong Kong. A bare year(ts) follows the SESSION time zone,
    so the model must declare the zone used to derive Year and the planner must not rely on the session."""
    ts = "TIMESTAMPTZ '2026-12-31 23:30:00+00'"
    c = duckdb.connect()
    c.execute("SET TimeZone = 'UTC'")
    utc_session = c.execute(f"SELECT year({ts})").fetchone()[0]
    c.execute("SET TimeZone = 'Asia/Hong_Kong'")
    hk_session = c.execute(f"SELECT year({ts})").fetchone()[0]
    declared = c.execute(f"SELECT year({ts} AT TIME ZONE 'UTC')").fetchone()[0]  # declared zone, session independent
    assert (utc_session, hk_session, declared) == (2026, 2027, 2026)


def test_ec_ctor_above_one_when_a_click_has_no_open(sc):
    """EC-CTOR-GT-ONE: image blocking can record a click without an open. The ratio is then above 100 percent (data check DB-DQ)."""
    c = sc
    c.execute("CREATE OR REPLACE TABLE m AS SELECT * FROM (VALUES (TRUE, FALSE, TRUE), (TRUE, TRUE, FALSE)) t(is_delivered, is_opened, is_clicked)")
    r = run(c, "SELECT COUNT(*) FILTER (WHERE is_clicked) * 1.0 / NULLIF(COUNT(*) FILTER (WHERE is_opened), 0) AS ctor FROM m")
    assert r[0]["ctor"] == 1.0 and run(c, "SELECT COUNT(*) FILTER (WHERE is_clicked AND NOT is_opened) AS bad FROM m")[0]["bad"] == 1


def test_ec_dimension_cap_and_duplicates_fail_closed():
    dims = [f"d{i}" for i in range(MAX_DIMS + 1)]
    with pytest.raises(ValueError, match="PLAN_TOO_MANY_DIMS"):
        plan_sql("message", ATOMS, KPIS, dims, [])
    with pytest.raises(ValueError, match="PLAN_DUPLICATE_DIM"):
        plan_sql("message", ATOMS, KPIS, ["typology"], ["typology"])


# ----------------------------------------------------------------------------------------------
# ART-VERIFY  The article numbers, re-run independently.
# ----------------------------------------------------------------------------------------------
@pytest.fixture(scope="module", params=["duckdb", "databricks"])
def retail(request):
    c = _dbx_conn() if request.param == "databricks" else duckdb.connect()
    return _load(c, "retail_poc.sql")


def test_article_wrong_totals(retail):
    r = run(
        retail,
        """WITH by_boutique AS (
             SELECT b.market, b.boutique_name, SUM(s.net_amount) AS net_sales, COUNT(*) AS transactions,
                    COUNT(DISTINCT s.client_id) AS active_clients, SUM(s.net_amount) / COUNT(*) AS avg_basket
             FROM sales_txn s JOIN boutique b USING (boutique_id)
             WHERE s.txn_date >= DATE '2026-10-01' AND s.txn_date < DATE '2026-11-01'
             GROUP BY b.market, b.boutique_name)
           SELECT market, SUM(active_clients) AS clients_summed, AVG(avg_basket) AS avg_of_avg,
                  SUM(net_sales) / SUM(transactions) AS avg_correct
           FROM by_boutique GROUP BY market ORDER BY market""",
    )
    hk = r[0]
    assert (hk["market"], hk["clients_summed"], float(hk["avg_of_avg"]), float(hk["avg_correct"])) == ("HK", 4, 1300.0, 1200.0)


def test_article_fanout(retail):
    r = run(
        retail,
        """SELECT b.market, COUNT(DISTINCT m.message_id) AS true_msgs, COUNT(*) AS naive_msgs, SUM(s.net_amount) AS naive_sales
           FROM message_sent m JOIN boutique b ON m.market=b.market
           JOIN sales_txn s ON s.boutique_id=b.boutique_id AND s.txn_date >= DATE '2026-10-01' AND s.txn_date < DATE '2026-11-01'
           GROUP BY b.market ORDER BY b.market""",
    )
    assert (r[0]["true_msgs"], r[0]["naive_msgs"], float(r[0]["naive_sales"])) == (5, 25, 30000.0)


def test_article_distinct_union_and_conversion(retail):
    users = run(retail, "SELECT channel, COUNT(DISTINCT client_id) AS u FROM message_sent GROUP BY channel ORDER BY channel")
    assert [u["u"] for u in users] == [5, 2, 2]
    assert run(retail, "SELECT COUNT(DISTINCT client_id) AS u FROM message_sent")[0]["u"] == 6
    conv = run(
        retail,
        """WITH reached AS (SELECT DISTINCT channel, client_id FROM message_sent),
                buyers AS (SELECT DISTINCT client_id FROM sales_txn WHERE txn_date >= DATE '2026-10-01' AND txn_date < DATE '2026-11-01'),
                cg AS (SELECT r.channel, r.client_id, b.client_id IS NOT NULL AS purchased FROM reached r LEFT JOIN buyers b USING (client_id))
           SELECT channel, COUNT(DISTINCT client_id) AS reached, COUNT(DISTINCT client_id) FILTER (WHERE purchased) AS converted
           FROM cg GROUP BY GROUPING SETS ((channel), ()) ORDER BY channel NULLS LAST""",
    )
    assert [(r["channel"], r["reached"], r["converted"]) for r in conv] == [
        ("Email", 5, 5), ("SMS", 2, 1), ("WeChat", 2, 2), (None, 6, 5)
    ]
    assert 5 + 2 + 2 == 9 and 5 + 1 + 2 == 8  # summed channel rows say 8/9 = 0.889, truth is 5/6 = 0.833


def test_article_yoy_table(retail):
    r = run(
        retail,
        """SELECT b.market, SUM(s.net_amount) FILTER (WHERE s.txn_date >= DATE '2026-10-01' AND s.txn_date < DATE '2026-11-01') AS cur,
                  SUM(s.net_amount) FILTER (WHERE s.txn_date >= DATE '2025-10-01' AND s.txn_date < DATE '2025-11-01') AS py
           FROM sales_txn s JOIN boutique b USING (boutique_id) GROUP BY ROLLUP (b.market) ORDER BY b.market NULLS LAST""",
    )
    got = [(x["market"], float(x["cur"]), float(x["py"])) for x in r]
    assert got == [("HK", 6000.0, 6000.0), ("SG", 5000.0, 4000.0), (None, 11000.0, 10000.0)]


# ----------------------------------------------------------------------------------------------
# PLAN-DRILL  Two facts meet at a conformed dimension WITHOUT row multiplication (article R5).
# ----------------------------------------------------------------------------------------------
def test_drill_across_matches_per_fact_oracle_and_avoids_fanout(retail):
    oct26 = "{c} >= DATE '2026-10-01' AND {c} < DATE '2026-11-01'"
    parts = [
        Part("msg", "message_sent", (Atom("messages", "COUNT(*)"),), oct26.format(c="sent_date")),
        Part(
            "sales",
            "(SELECT s.*, b.market FROM sales_txn s JOIN boutique b USING (boutique_id))",
            (Atom("net_sales", "SUM(net_amount)"),),
            oct26.format(c="txn_date"),
        ),
    ]
    out = run(retail, drill_across_sql(parts, ["market"], [("market",), ()]) + " ORDER BY market NULLS LAST")
    got = [(r["market"], r["gid"], r["messages"], float(r["net_sales"])) for r in out]
    assert got == [("HK", 0, 5, 6000.0), ("SG", 0, 5, 5000.0), (None, 1, 10, 11000.0)]
    # the row-level join the article warns about gives 25 rows and 30,000 for HK (test_article_fanout)
    assert got[0][3] == 6000.0 != 30000.0


# ----------------------------------------------------------------------------------------------
# EDGE-*  Integration with EdgeSQL (https://github.com/raphaelmansuy/EdgeSQL, commit 8777868 when written).
# Skipped when edgesql is not installed. See ../10-edgesql-integration.md
# ----------------------------------------------------------------------------------------------
def test_edge_parses_and_round_trips_planner_sql_for_databricks():
    """EDGE-OK-01: the planner output is valid input for EdgeSQL, and its writer is stable (parse -> emit -> parse -> emit)."""
    edgesql = pytest.importorskip("edgesql")
    sqls = [
        plan_sql("message", ATOMS, KPIS, ROWS, COLS),
        drill_across_sql(
            [Part("msg", "message_sent", (Atom("messages", "COUNT(*)"),)), Part("sales", "sales_txn", (Atom("net_sales", "SUM(net_amount)"),))],
            ["market"],
            [("market",), ()],
        ),
    ]
    for sql in sqls:
        once = edgesql.Query.parse(sql, dialect="databricks").to_sql()
        assert edgesql.Query.parse(once, dialect="databricks").to_sql() == once


def test_edge_can_inspect_tables_and_inject_a_typed_filter_into_the_agg_scope():
    """EDGE-OK-02: inspection names the fact table, and and_where on the CTE scope adds a bound parameter."""
    edgesql = pytest.importorskip("edgesql")
    q = edgesql.Query.parse(plan_sql("message", ATOMS, KPIS, ROWS, COLS), dialect="databricks")
    assert q.tables() == ["message"] and q.ctes() == ["agg"]
    out = q.cte("agg").and_where(edgesql.col("yr").gte(edgesql.param("start_year"))).to_sql()
    assert ":start_year" in out


@pytest.mark.xfail(strict=True, reason="EDGE-GAP-01: a {{ slot }} is printed as {?}, so its name is lost on emit")
def test_edge_gap_01_template_slot_keeps_its_name():
    edgesql = pytest.importorskip("edgesql")
    q = edgesql.Query.parse("SELECT {{ group_by_list }}, COUNT(*) AS kpi_value FROM message", dialect="databricks")
    assert "group_by_list" in q.to_sql()


@pytest.mark.xfail(strict=True, reason="EDGE-GAP-02: params() lists a {{ slot }} twice")
def test_edge_gap_02_slot_is_listed_once():
    edgesql = pytest.importorskip("edgesql")
    q = edgesql.Query.parse("SELECT {{ group_by_list }}, COUNT(*) AS kpi_value FROM message", dialect="databricks")
    assert q.params() == [{"param": "group_by_list"}]


def test_drill_across_keeps_null_member_and_subtotal_apart(sc):
    """EC-NULL-MEMBER x PLAN-DRILL: the join key is (gid, dims). Without gid, the unknown-market row would also
    match the grand-total row of the other fact (both have market NULL). Found by mutation M4."""
    c = sc
    c.execute("CREATE OR REPLACE TABLE a AS SELECT * FROM (VALUES ('HK', 1), (NULL, 1), (NULL, 1)) t(market, v)")
    c.execute("CREATE OR REPLACE TABLE b AS SELECT * FROM (VALUES ('HK', 10), (NULL, 10)) t(market, w)")
    parts = [Part("pa", "a", (Atom("n", "COUNT(*)"),)), Part("pb", "b", (Atom("total_w", "SUM(w)"),))]
    out = run(c, drill_across_sql(parts, ["market"], [("market",), ()]) + " ORDER BY gid, market NULLS LAST")
    assert [(r["market"], r["gid"], r["n"], r["total_w"]) for r in out] == [
        ("HK", 0, 1, 10),
        (None, 0, 2, 10),  # unknown member: 2 rows in a, 1 row of weight 10 in b
        (None, 1, 3, 20),  # grand total
    ]
