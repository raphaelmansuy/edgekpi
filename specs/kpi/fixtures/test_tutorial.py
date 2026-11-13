"""Checks the eight-message worked example in ../START-HERE.md.
The local and opt-in Databricks fixtures exercise counts, rates, overlap and fan-out;
this file does not prove production behavior or warehouse timings."""
from __future__ import annotations

import pytest

from mini_planner import plan_sql
from test_fixtures import ATOMS, KPIS, run, sc  # noqa: F401

MSG = """CREATE OR REPLACE TABLE tut_msg AS SELECT * FROM (VALUES
 (1,'c1','New','HK',TRUE ,TRUE ,TRUE ),
 (2,'c1','New','HK',TRUE ,TRUE ,FALSE),
 (3,'c2','New','HK',FALSE,FALSE,FALSE),
 (4,'c3','New','SG',TRUE ,TRUE ,FALSE),
 (5,'c4','VIP','HK',TRUE ,TRUE ,TRUE ),
 (6,'c4','VIP','SG',TRUE ,FALSE,FALSE),
 (7,'c5','VIP','SG',TRUE ,TRUE ,TRUE ),
 (8,'c5','VIP','SG',FALSE,FALSE,FALSE)
) AS t(message_id, client_id, typology, market, is_delivered, is_opened, is_clicked)"""
EVENTS = """CREATE OR REPLACE TABLE tut_open_event AS SELECT * FROM (VALUES
 (1,'open'),(1,'open'),(1,'open'),(2,'open'),(4,'open'),(5,'open'),(7,'open')
) AS t(message_id, kind)"""


@pytest.fixture
def tut(sc):
    sc.execute(MSG)
    sc.execute(EVENTS)
    return sc


@pytest.fixture
def grid(tut):
    out = run(tut, plan_sql("tut_msg", ATOMS, KPIS, ["typology"], ["market"]))
    return {(d["typology"], d["market"]): d for d in out}


def pct(x):
    return None if x is None else round(x * 100, 1)


def test_tutorial_step1_the_cells(grid):
    cells = {k: (v["sent"], v["delivered"], v["clients"], pct(v["delivery_rate"])) for k, v in grid.items() if None not in k}
    assert cells == {
        ("New", "HK"): (3, 2, 2, 66.7),
        ("New", "SG"): (1, 1, 1, 100.0),
        ("VIP", "HK"): (1, 1, 1, 100.0),
        ("VIP", "SG"): (3, 2, 2, 66.7),
    }


def test_tutorial_step2_averaging_scalar_cells_gives_wrong_totals(grid):
    cell_rates = [grid[k]["delivery_rate"] for k in grid if None not in k]
    assert pct(sum(cell_rates) / 4) == 83.3  # mean of the four cells
    assert pct(grid[(None, None)]["delivery_rate"]) == 75.0  # truth: 6 / 8
    new_rate = [grid[("New", m)]["delivery_rate"] for m in ("HK", "SG")]
    assert pct(sum(new_rate) / 2) == 83.3 and pct(grid[("New", None)]["delivery_rate"]) == 75.0
    # unique clients: add the cells and you invent a client
    assert sum(grid[k]["clients"] for k in grid if None not in k) == 6
    assert grid[(None, None)]["clients"] == 5
    assert grid[("VIP", "HK")]["clients"] + grid[("VIP", "SG")]["clients"] == 3 and grid[("VIP", None)]["clients"] == 2
    assert grid[(None, "HK")]["clients"] + grid[(None, "SG")]["clients"] == 6  # the two market totals, added


def test_tutorial_step3_one_statement_gives_every_total_right(grid):
    assert len(grid) == 9  # 4 cells + 2 typology totals + 2 market totals + 1 grand total
    got = {k: (v["sent"], v["delivered"], v["opened"], v["clicked"], v["clients"]) for k, v in grid.items()}
    assert got == {
        ("New", "HK"): (3, 2, 2, 1, 2), ("New", "SG"): (1, 1, 1, 0, 1),
        ("VIP", "HK"): (1, 1, 1, 1, 1), ("VIP", "SG"): (3, 2, 1, 1, 2),
        ("New", None): (4, 3, 3, 1, 3), ("VIP", None): (4, 3, 2, 2, 2),
        (None, "HK"): (4, 3, 3, 2, 3), (None, "SG"): (4, 3, 2, 1, 3),
        (None, None): (8, 6, 5, 3, 5),
    }
    assert {k: v["gid"] for k, v in grid.items()} == {
        ("New", "HK"): 0, ("New", "SG"): 0, ("VIP", "HK"): 0, ("VIP", "SG"): 0,
        ("New", None): 1, ("VIP", None): 1, (None, "HK"): 2, (None, "SG"): 2, (None, None): 3,
    }


def test_tutorial_step4_ratios_of_totals_for_the_other_kpis(grid):
    assert pct(grid[(None, None)]["open_rate"]) == 83.3  # 5 / 6
    assert pct(sum(grid[k]["open_rate"] for k in grid if None not in k) / 4) == 87.5  # mean of cells
    assert pct(grid[("VIP", None)]["open_rate"]) == 66.7  # 2 / 3
    assert pct((grid[("VIP", "HK")]["open_rate"] + grid[("VIP", "SG")]["open_rate"]) / 2) == 75.0  # mean of its cells


def test_tutorial_step5_ctor_is_composed_not_stored(grid):
    order = [("New", "HK"), ("New", "SG"), ("VIP", "HK"), ("VIP", "SG")]
    cells = [grid[k] for k in order]
    assert [pct(c["ctor"]) for c in cells] == [50.0, 0.0, 100.0, 100.0]
    assert pct(grid[(None, None)]["ctor"]) == 60.0  # 3 clicked / 5 opened
    assert pct(sum(c["ctor"] for c in cells) / 4) == 62.5  # mean of the four cell CTORs
    assert pct(grid[("New", None)]["ctor"]) == 33.3 and pct((grid[("New", "HK")]["ctor"] + grid[("New", "SG")]["ctor"]) / 2) == 25.0


def test_tutorial_step6_naive_per_kpi_per_shape_baseline():
    kpis, nodes = 6, 4  # 4 nodes here: cells, typology totals, market totals, grand total
    assert kpis * nodes == 24


def test_tutorial_step7_joining_events_miscounts_messages(tut):
    naive = run(tut, "SELECT COUNT(*) AS sent, COUNT(*) AS opens FROM tut_msg m JOIN tut_open_event e USING (message_id)")[0]
    right = run(tut, "SELECT COUNT(*) AS sent, COUNT(*) FILTER (WHERE is_opened) AS opened FROM tut_msg")[0]
    assert (naive["sent"], naive["opens"]) == (7, 7)  # 3 messages vanish, message 1 counted 3 times
    assert (right["sent"], right["opened"]) == (8, 5)


def test_tutorial_step8_a_view_of_a_rate_cannot_be_regrouped(tut, grid):
    """SQL composes relations, not measures: a relation that stores a finished rate at one grain has no
    correct re-aggregation at another (05, 'Is the root cause that SQL is not composable?').
    The view is written as a CTE so the test creates no persistent object."""
    regrouped = run(tut, """WITH kpi_delivery AS (
          SELECT typology, market, COUNT(*) FILTER (WHERE is_delivered) * 1.0 / COUNT(*) AS delivery_rate
          FROM tut_msg GROUP BY typology, market)
        SELECT typology, AVG(delivery_rate) AS delivery_rate FROM kpi_delivery GROUP BY typology""")
    assert {r["typology"]: pct(r["delivery_rate"]) for r in regrouped} == {"New": 83.3, "VIP": 83.3}
    assert pct(grid[("New", None)]["delivery_rate"]) == pct(grid[("VIP", None)]["delivery_rate"]) == 75.0
