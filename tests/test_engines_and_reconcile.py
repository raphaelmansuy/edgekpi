"""Reconciliation, engine failure, grain and capability limits. EC-L-09 EC-L-11 EC-L-13 EC-L-14 EC-L-15 EC-L-24 EC-L-25"""
import pytest

from edgekpi import (EngineError, GeneratedSql, ReportRequest, UnsupportedError, reconcile, run, validate)
from edgekpi.backends.malloy import Malloy
from edgekpi.backends.metric_view import MetricView
from edgekpi.errors import GrainError, ReconciliationError
from edgekpi.grain import check_joins
from edgekpi.grid import Grid
from edgekpi.scopes import lattice


def good_grid(model, duck):
    return run(model, {"kpis": ["sent", "delivery_rate", "reached"], "rows": ["typology"], "cols": ["market"]}, GeneratedSql(), duck).grid


def test_a_correct_grid_passes_every_invariant(model, duck):
    assert reconcile.check(good_grid(model, duck), model) == []


def test_a_wrong_part_is_caught_and_the_node_is_named(model, duck):
    """EC-L-15: C-PARTS."""
    grid = good_grid(model, duck)
    node = next(n for n in grid.cells if n.scope == ("typology", "market") and n.members == ("New", "HK"))
    grid.cells[node]["n_sent"] += 1
    violations = reconcile.check(grid, model)
    assert violations and any("n_sent" in v.message for v in violations)
    with pytest.raises(ReconciliationError) as caught:
        reconcile.assert_reconciled(grid, model)
    assert caught.value.code in ("C-PARTS", "C-RATE")


def test_a_rate_that_is_not_its_own_numerator_over_denominator_is_caught(model, duck):
    """EC-L-15: C-RATE, the averaged-rate error the business case is about."""
    grid = good_grid(model, duck)
    node = next(n for n in grid.cells if n.scope == ())
    grid.cells[node]["delivery_rate"] = 0.5
    violations = reconcile.check(grid, model)
    assert [v.code for v in violations] == ["C-RATE"] and violations[0].node == ()


def test_a_distinct_count_that_is_summed_is_caught_by_its_bound(model, duck):
    """EC-L-14: the distinct count of the whole never exceeds the sum of its parts; one that does was summed wrongly."""
    grid = good_grid(model, duck)
    node = next(n for n in grid.cells if n.scope == ())
    parts = sum(v["n_reached"] for n, v in grid.cells.items() if n.scope == ("typology",))
    grid.cells[node]["n_reached"] = parts + 1
    assert any(v.code == "C-BOUND" for v in reconcile.check(grid, model))


def test_distinct_counts_are_not_required_to_add_up(model, duck):
    """EC-L-14: a client reached in two markets is one reached client in total, so parts may sum to more than the whole."""
    grid = good_grid(model, duck)
    by_market = sum(v["n_reached"] for n, v in grid.cells.items() if n.scope == ("market",))
    assert grid.get(())["n_reached"] < by_market
    assert reconcile.check(grid, model) == []


def test_a_missing_parent_is_reported(model, duck):
    grid = good_grid(model, duck)
    del grid.cells[next(n for n in grid.cells if n.scope == ())]
    requested = lattice(("typology",), ("market",))
    assert any("parent node is missing" in v.message for v in reconcile.check(grid, model, requested))


def test_run_can_raise_flag_or_skip_the_check(model, duck, monkeypatch):
    request = {"kpis": ["sent"], "rows": ["market"]}
    backend = GeneratedSql()
    original = backend.assemble

    def corrupt(plan, rows):
        grid = original(plan, rows)
        grid.cells[next(n for n in grid.cells if n.scope == ())]["n_sent"] += 5
        return grid

    monkeypatch.setattr(backend, "assemble", corrupt)
    with pytest.raises(ReconciliationError) as caught:
        run(model, request, backend, duck)
    assert caught.value.detail["states"][-1] == "FAILED"
    assert run(model, request, backend, duck, reconcile="flag").violations
    assert run(model, request, backend, duck, reconcile="off").violations == []


class ScriptedEngine:
    def __init__(self, name, fail_on=None, rows=()):
        self.name, self.fail_on, self.calls, self.rows = name, fail_on, 0, list(rows)

    def execute(self, statement):
        self.calls += 1
        if self.calls == self.fail_on:
            raise EngineError("ENGINE_FAILED", "boom")
        return self.rows


def test_an_engine_failure_returns_no_partial_grid(model):
    """EC-L-24."""
    with pytest.raises(EngineError) as caught:
        run(model, {"kpis": ["sent"]}, GeneratedSql(), ScriptedEngine("duckdb", fail_on=1))
    assert caught.value.detail["states"] == ["VALIDATED", "COMPILED", "FAILED"]


def test_a_failure_after_the_ddl_still_fails_the_whole_plan(model):
    """EC-L-24: the metric-view plan has two statements; the second failing must not yield a grid."""
    engine = ScriptedEngine("databricks", fail_on=2)
    with pytest.raises(EngineError):
        run(model, {"kpis": ["sent"]}, MetricView(), engine)
    assert engine.calls == 2


def test_an_unexpected_exception_is_wrapped_with_the_state(model):
    class Broken:
        name = "duckdb"

        def execute(self, statement):
            raise RuntimeError("socket closed")

    with pytest.raises(EngineError) as caught:
        run(model, {"kpis": ["sent"]}, GeneratedSql(), Broken())
    assert caught.value.code == "ENGINE_FAILED" and "socket closed" in caught.value.message


def test_a_backend_cannot_run_on_an_engine_it_does_not_support(model):
    """EC-L-11: the metric view is a Databricks object; asking DuckDB to run it is refused before anything executes."""
    engine = ScriptedEngine("duckdb")
    with pytest.raises(UnsupportedError) as caught:
        run(model, {"kpis": ["sent"]}, MetricView(), engine)
    assert caught.value.code == "ENGINE_MISMATCH" and engine.calls == 0


def test_an_engine_returning_a_scope_nobody_asked_for_is_refused(model):
    """EC-L-13: the library never trusts a row it cannot place."""
    engine = ScriptedEngine("duckdb", rows=[{"typology": "New", "gid": 1, "edgekpi_rows": 1, "n_sent": 1, "sent": 1}])
    request = {"kpis": ["sent"], "rows": ["typology"], "cols": ["market"], "totals": {"rows": False, "cols": False}}
    with pytest.raises(EngineError) as caught:
        run(model, request, GeneratedSql(), engine)
    assert caught.value.code == "ENGINE_UNEXPECTED_SCOPE"


def test_a_malloy_result_with_a_missing_nest_is_refused(model):
    """EC-L-13."""
    plan = Malloy().compile(validate(model, ReportRequest(kpis=("sent",), rows=("market",))))
    with pytest.raises(EngineError) as caught:
        Malloy().assemble(plan, [{"edgekpi_rows": 3, "n_sent": 3, "sent": 3}])
    assert caught.value.code == "ENGINE_INCOMPLETE_RESULT"
    with pytest.raises(EngineError):
        Malloy().assemble(plan, [])


def test_a_duplicate_node_in_one_result_is_refused():
    grid = Grid(("a",), ("n",), ())
    grid.add(("a",), (1,), {"n": 1})
    with pytest.raises(ValueError):
        grid.add(("a",), (1,), {"n": 2})


def test_members_and_values_have_one_representation_whatever_the_engine_returned():
    """EC-L-30: Decimal, float, date and int spellings of the same member must meet in one node."""
    import datetime
    import decimal

    from edgekpi.grid import canon
    assert canon(decimal.Decimal("3")) == 3 and canon(3.0) == 3 and canon(2.5) == 2.5
    assert canon(datetime.date(2026, 1, 1)) == "2026-01-01" and canon(None) is None and canon(True) is True and canon("x") == "x"
    grid = Grid(("y",), ("n",), ())
    grid.add(("y",), (2026.0,), {"n": decimal.Decimal("7")})
    assert grid.get(("y",), 2026)["n"] == 7


def test_a_non_unique_key_is_refused(duck):
    """EC-L-25."""
    duck.con.execute("CREATE OR REPLACE TABLE dup AS SELECT * FROM (VALUES (1, 'a'), (1, 'b')) AS t(id, v)")
    with pytest.raises(GrainError) as caught:
        check_joins(duck, "dup", "id", [])
    assert caught.value.code == "GRAIN_KEY_NOT_UNIQUE"


def test_a_fanout_join_is_refused_with_the_counts(duck):
    """EC-L-09."""
    with pytest.raises(GrainError) as caught:
        check_joins(duck, "message", "message_id", [("message_event", "e", "source.message_id = e.message_id")])
    assert caught.value.code == "GRAIN_JOIN_FANOUT"
    assert caught.value.detail["fact_rows"] == 13 and caught.value.detail["joined_rows"] > 13


def test_a_one_to_one_join_passes_and_reports_what_it_saw(duck):
    seen = check_joins(duck, "message", "message_id", [("client", "client", "source.client_id = client.client_id")])
    assert seen == {"fact_rows": 13, "joined_rows": 13, "distinct_keys": 13}


def test_a_dimension_table_with_a_duplicated_row_is_caught_as_fanout(duck):
    """EC-L-09: the silent way a correct-looking join starts to double count."""
    duck.con.execute("CREATE OR REPLACE TABLE client2 AS SELECT * FROM client UNION ALL SELECT * FROM client WHERE client_id = 'c1'")
    with pytest.raises(GrainError):
        check_joins(duck, "message", "message_id", [("client2", "client2", "source.client_id = client2.client_id")])
