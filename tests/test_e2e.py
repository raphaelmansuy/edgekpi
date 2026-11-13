"""End to end: every request of the matrix, through every backend/engine pair, against the independent reference.

Covers: EC-L-01 EC-L-02 EC-L-03 EC-L-13 EC-L-17 EC-L-19 EC-L-21 EC-L-23 EC-L-26 EC-L-30
"""
import pytest
from conftest import PAIRS, REQUESTS

from edgekpi import ReportRequest, compare, reference, run, validate


@pytest.mark.parametrize("pair", PAIRS, indirect=True)
@pytest.mark.parametrize("name", REQUESTS)
def test_backend_matches_the_independent_reference(model, duck, pair, name):
    label, backend, engine = pair
    request = ReportRequest.from_dict(REQUESTS[name])
    result = run(model, request, backend, engine, reconcile="flag")
    expected = reference(validate(model, request), duck)
    assert compare(result.grid, expected) == [], f"{label} differs on {name}"
    assert result.violations == [], f"{label} breaks an invariant on {name}"
    assert result.states == ["VALIDATED", "COMPILED", "EXECUTED", "ASSEMBLED", "RECONCILED"]


def test_matrix_reaches_the_edge_cases_it_claims(model, duck):
    """The matrix is only a proof if its data really contains the cases (guards against a fixture drifting)."""
    def grid(name):
        return run(model, REQUESTS[name], __import__("edgekpi").GeneratedSql(), duck).grid

    assert len(grid("empty-input")) == 0, "EC-L-01: no input rows, no node, not even a zero grand total"
    zero = grid("zero-denominator-group")
    assert zero.get(("market",), "JP")["delivery_rate"] == 0.0 and zero.get(("market",), "JP")["open_rate"] is None, "EC-L-02"
    assert grid("grand-total-only").get(())["sent"] == 13, "EC-L-26"
    assert {n.scope for n in grid("totals-off").cells} == {("typology", "market")}, "EC-L-19"
    typologies = {n.members[0] for n in grid("two-row-levels").cells if n.scope == ("typology",)}
    assert None in typologies and "New" in typologies, "EC-L-03: the unknown client is a NULL member"
    assert grid("two-row-levels").get(()) is not None, "the grand total is a different node from the NULL member"
    # EC-L-17: a filter that is not on an axis still applies at the grand total
    assert grid("where-eq-off-axis").get(())["sent"] == 9
    # EC-L-21: the end date is excluded: message 12 is dated exactly 2025-12-31
    ends = grid("end-date-only")
    assert ends.get(())["sent"] == 4
