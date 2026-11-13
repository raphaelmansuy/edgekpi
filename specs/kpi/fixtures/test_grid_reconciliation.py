"""C-CHECK in ../16-correctness-contract.md: a correct grid reconciles with itself, and what that does not prove.

The S4 tests run on DuckDB and, when the Databricks tier is enabled, on the warehouse fixture.
"""
from __future__ import annotations

import copy

import pytest

from grid_checks import index_nodes, lattice_edges, reconcile, relation, shape_of
from mini_planner import grouping_sets, plan_sql
from test_fixtures import ALL_DIMS, ATOMS, COLS, KPIS, ROWS, con, grid, pick, run, sc  # noqa: F401

ADDITIVE = ["sent", "delivered", "opened", "clicked"]
RATIOS = [("delivery_rate", "delivered", "sent"), ("open_rate", "opened", "delivered"),
          ("click_rate", "clicked", "delivered"), ("ctor", "clicked", "opened")]
DISTINCT = ["clients"]


def check(rows):
    return reconcile(rows, ALL_DIMS, ADDITIVE, RATIOS, DISTINCT)


def total(rows):
    return pick(rows, None, None, None, None, None)


def test_s4_grid_reconciles_on_every_lattice_edge(grid):
    """12 shapes form a 4 x 3 product of chains: 3*3 row steps + 2*4 column steps = 17 parent/child edges."""
    edges = lattice_edges(shape_of(r, ALL_DIMS) for r in grid)
    assert len(edges) == 17
    assert {shape_of(r, ALL_DIMS) for r in grid} == set(grouping_sets(ROWS, COLS))
    assert check(grid) == []


def test_a_real_null_member_is_a_child_and_not_a_total(sc):
    """An unknown market is one member of the partition. Reading totals from NULLs would break the check."""
    sc.execute("""CREATE OR REPLACE TABLE recon_msg AS SELECT * FROM (VALUES
        ('New','HK','c1',TRUE,TRUE,FALSE), ('New',NULL,'c1',TRUE,FALSE,FALSE), ('New',NULL,'c2',FALSE,FALSE,FALSE),
        ('VIP','SG','c3',TRUE,TRUE,TRUE)) AS t(typology, market, client_id, is_delivered, is_opened, is_clicked)""")
    rows = run(sc, plan_sql("recon_msg", ATOMS, KPIS, ["typology"], ["market"]))
    dims = ["typology", "market"]
    nodes = index_nodes(rows, dims)
    assert nodes[(("typology", "market"), ("New", None))]["sent"] == 2  # unknown market: a detail member
    assert nodes[(("typology",), ("New",))]["sent"] == 3               # all markets: the total
    assert reconcile(rows, dims, ADDITIVE, RATIOS, DISTINCT) == []


def test_reconciliation_detects_mixed_snapshots_and_truncated_results(grid):
    """Failures that leave each number plausible on its own: a total read after one more message was
    ingested (split plan without pinned versions), and a result that lost a row (unread chunk)."""
    late = copy.deepcopy(grid)
    total(late)["sent"] += 1
    kinds = {v[0] for v in check(late)}
    assert "additive" in kinds and "formula" in kinds

    truncated = [r for r in grid if (r["campaign"], r["yr"], r["market"]) != ("C", 2026, "SG")]
    assert len(truncated) == len(grid) - 1
    assert any(v[0] == "additive" for v in check(truncated))


def test_an_averaged_rate_passes_the_bounds_and_fails_the_formula(grid):
    """The mean of child rates always lies between the smallest and largest child, so bounds cannot catch it.
    Recomputing the rate from the node's own numerator and denominator does."""
    averaged = copy.deepcopy(grid)
    campaigns = [pick(grid, t, ti, c, None, None)["delivery_rate"] for t, ti, c in
                 [("New", "Gold", "A"), ("New", "Gold", "B"), ("Existing", "Silver", "C")]]
    total(averaged)["delivery_rate"] = sum(campaigns) / len(campaigns)
    violations = check(averaged)
    assert violations and {v[0] for v in violations} == {"formula"}


def test_reconciliation_cannot_see_an_error_repeated_at_every_scope(grid):
    """A join that duplicates every message doubles detail and totals alike. The grid still reconciles,
    so grain and key-uniqueness checks on the source remain necessary (FP-6)."""
    doubled = copy.deepcopy(grid)
    for row in doubled:
        for atom in ADDITIVE:
            row[atom] *= 2
    assert check(doubled) == []
    assert total(doubled)["sent"] == 2 * total(grid)["sent"]


def test_a_summed_audience_is_caught_only_when_another_breakdown_bounds_it(grid):
    """Adding unique counts lands exactly on the upper bound of I3. With two breakdowns of the same node the
    smaller sum exposes it; with one breakdown it passes, so exact distincts still need evaluation at scope."""
    summed = copy.deepcopy(grid)
    gold = pick(summed, "New", "Gold", None, None, None)
    gold["clients"] = 240                      # campaigns A + B; the two years add to 235, the truth is 120
    assert any(v[0] == "distinct_bounds" for v in check(summed))

    one_breakdown = [
        {"gid": 0, "typology": "VIP", "market": "HK", "sent": 1, "clients": 1},
        {"gid": 0, "typology": "VIP", "market": "SG", "sent": 3, "clients": 2},
        {"gid": 1, "typology": "VIP", "market": None, "sent": 4, "clients": 3},   # 1 + 2; the truth is 2
    ]
    assert reconcile(one_breakdown, ["typology", "market"], ["sent"], distinct=["clients"]) == []


def test_additivity_probe_separates_counts_rates_and_distincts(grid):
    """Behaviour over partitions classifies an unknown KPI without reading its SQL (EDGE-PROBE).
    Additivity belongs to a (measure, partition) pair: unique clients add up across typologies here,
    because no client belongs to two, and do not add up across markets, years or campaigns."""
    grand = total(grid)
    years = [pick(grid, None, None, None, y, None) for y in (2025, 2026)]
    typologies = [pick(grid, t, None, None, None, None) for t in ("New", "Existing")]
    markets_2025 = [pick(grid, None, None, None, 2025, m) for m in ("HK", "SG")]
    campaigns = [pick(grid, "New", "Gold", c, None, None) for c in ("A", "B")]
    gold = pick(grid, "New", "Gold", None, None, None)

    for parts in (years, typologies):
        assert relation(grand["sent"], [p["sent"] for p in parts]) == "equals_sum"
        assert relation(grand["delivery_rate"], [p["delivery_rate"] for p in parts]) == "within_range"

    assert relation(grand["clients"], [p["clients"] for p in typologies]) == "equals_sum"       # 120 + 60 = 180
    assert relation(years[0]["clients"], [p["clients"] for p in markets_2025]) == "below_sum"   # 165 + 125 > 175 > 165
    # One part can contain the others (175, 180 -> 180; 120, 120 -> 120): that reading alone is ambiguous.
    assert relation(grand["clients"], [p["clients"] for p in years]) == "at_max"
    assert relation(gold["clients"], [p["clients"] for p in campaigns]) == "at_max"
    assert relation(5, [5]) == "uninformative" and relation(9, [2, 3]) == "inconsistent"
