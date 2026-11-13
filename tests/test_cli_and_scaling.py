"""The command line, and scaling checks with generous bounds. EC-L-12 plus the O(n) claims of docs/07-complexity."""
import json
import time

import pytest
from conftest import DATA, EXAMPLES, MODEL_PATH, REQUESTS

from edgekpi import Dimension, Kpi, Measure, ReportRequest, SemanticModel, reconcile, validate
from edgekpi.backends.malloy import Malloy
from edgekpi.backends.sql import GeneratedSql
from edgekpi.cli import main
from edgekpi.grid import Grid
from edgekpi.scopes import lattice


@pytest.fixture
def files(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(json.dumps(REQUESTS["pivot-with-params-and-where"]))
    data = tmp_path / "data.sql"
    data.write_text(DATA)
    return str(request), str(data)


def test_validate_prints_the_model_summary(capsys):
    assert main(["validate", str(MODEL_PATH)]) == 0
    out = capsys.readouterr().out
    assert "model engagement" in out and "n_reached[unique]" in out and "reached[unconfirmed]" in out and "from_date?" in out


def test_compile_prints_each_backend_s_statements(capsys, files):
    request, _ = files
    for backend, marker in (("sql", "GROUPING SETS"), ("metric-view", "WITH METRICS LANGUAGE YAML"), ("malloy", "nest: s0")):
        assert main(["compile", str(MODEL_PATH), request, "--backend", backend]) == 0
        assert marker in capsys.readouterr().out


def test_run_prints_a_pivot_with_every_total_and_the_reconciliation(capsys, files):
    request, data = files
    assert main(["run", str(MODEL_PATH), request, "--data", data]) == 0
    out = capsys.readouterr().out
    assert "| typology |     HK |     SG |   All |" in out and "| Total    |" in out
    assert "states: VALIDATED > COMPILED > EXECUTED > ASSEMBLED > RECONCILED" in out and "all checks pass" in out


@pytest.mark.malloy
def test_verify_compares_the_backends(capsys, files, malloy):
    request, data = files
    assert main(["verify", str(MODEL_PATH), request, "--data", data]) == 0
    out = capsys.readouterr().out
    assert "sql on duckdb" in out and "malloy on duckdb" in out and "DIFFER" not in out


def test_infer_prints_the_model_and_the_refusals(capsys, tmp_path):
    data = tmp_path / "data.sql"
    data.write_text(DATA)
    code = main(["infer", str(EXAMPLES / "templates.sql"), "--name", "registry", "--key", "message_id",
                 "--dim", "typology=client.typology", "--dim", "market=market", "--data", str(data)])
    out = capsys.readouterr().out
    assert code == 0 and "# accepted 6, refused 2" in out and "# refused open-events: GRAIN_JOIN_FANOUT" in out


def test_check_grain_reports_the_counts(capsys, tmp_path):
    data = tmp_path / "data.sql"
    data.write_text(DATA)
    assert main(["check-grain", str(MODEL_PATH), "--data", str(data)]) == 0
    assert "'fact_rows': 13" in capsys.readouterr().out


def test_a_library_error_is_printed_with_its_code_and_exits_one(capsys, tmp_path, files):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"kpis": ["ghost"]}))
    assert main(["compile", str(MODEL_PATH), str(bad)]) == 1
    assert capsys.readouterr().err.startswith("REQ_UNKNOWN_KPI")


# ---- scaling ------------------------------------------------------------------------------------------------------

def synthetic(members: int):
    """A grid of members x 10 detail nodes plus both subtotal families and the grand total, with correct parts."""
    grid = Grid(("a", "b"), ("n",), ())
    total = 0
    for i in range(members):
        row_total = 0
        for j in range(10):
            grid.add(("a", "b"), (i, j), {"n": 1})
            row_total += 1
        grid.add(("a",), (i,), {"n": row_total})
        total += row_total
    for j in range(10):
        grid.add(("b",), (j,), {"n": members})
    grid.add((), (), {"n": total})
    return grid


def test_reconciliation_time_grows_linearly_with_the_nodes():
    model = SemanticModel("m", "t", "id", (Measure("n", "COUNT(*)"),), (Kpi("k", "n"),), (Dimension("a", "a"), Dimension("b", "b")))
    scopes = lattice(("a",), ("b",))
    timings = {}
    for members in (4000, 8000, 16000):
        grid = synthetic(members)
        start = time.perf_counter()
        assert reconcile.check(grid, model, scopes) == []
        timings[members] = (time.perf_counter() - start, len(grid))
    (t1, n1), (t3, n3) = timings[4000], timings[16000]
    assert n3 / n1 == pytest.approx(4, rel=0.01)
    assert t3 / max(t1, 1e-6) < 4 * 2.5, f"4x the nodes took {t3 / t1:.1f}x the time: not linear ({timings})"


def test_compilation_cost_is_independent_of_data_and_grows_with_scopes_not_rows(model):
    """The statement size depends on dimensions and measures only: O(scopes x dims), never O(rows)."""
    sizes = []
    for dims in (["typology"], ["typology", "tier"], ["typology", "tier", "market"]):
        text = GeneratedSql().compile(validate(model, ReportRequest(kpis=("sent",), rows=tuple(dims)))).query.text
        sizes.append((len(dims), len(text)))
    assert sizes[0][1] < sizes[1][1] < sizes[2][1] < sizes[0][1] * 4


@pytest.mark.parametrize("rows, cols, expected", [(1, 1, 4), (2, 2, 9), (3, 3, 16), (4, 4, 25)])
def test_scope_count_is_rows_plus_one_times_cols_plus_one(rows, cols, expected):
    assert len(lattice(tuple("abcd"[:rows]), tuple("wxyz"[:cols]))) == expected


def test_the_malloy_statement_has_one_nest_per_scope_except_the_total(model):
    plan = Malloy().compile(validate(model, ReportRequest(kpis=("sent",), rows=("typology", "tier"), cols=("market",))))
    assert plan.query.text.count("nest: s") == 5            # 6 scopes, minus the grand total which is the top row
