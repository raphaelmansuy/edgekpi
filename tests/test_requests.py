"""Request validation and the scope lattice. EC-L-04 EC-L-05 EC-L-08 EC-L-12 EC-L-16 EC-L-22 EC-L-29"""
import datetime

import pytest

from edgekpi import ReportRequest, RequestError, validate
from edgekpi.scopes import axis_levels, gid, lattice, scope_of


def check(model, **fields) -> str:
    base = {"kpis": ["sent"]}
    with pytest.raises(RequestError) as caught:
        validate(model, ReportRequest.from_dict({**base, **fields}))
    return caught.value.code


@pytest.mark.parametrize("fields, expected", [
    ({"kpis": []}, "REQ_NO_KPIS"),
    ({"kpis": ["sent", "sent"]}, "REQ_DUPLICATE_KPI"),                                  # EC-L-04
    ({"kpis": ["ghost"]}, "REQ_UNKNOWN_KPI"),                                           # EC-L-05
    ({"kpis": ["n_sent"]}, "REQ_UNKNOWN_KPI"),                                          # a measure is not a KPI
    ({"rows": ["ghost"]}, "REQ_UNKNOWN_DIMENSION"),                                     # EC-L-05
    ({"rows": ["market"], "cols": ["market"]}, "REQ_DUPLICATE_DIMENSION"),              # EC-L-04
    ({"rows": ["market", "market"]}, "REQ_DUPLICATE_DIMENSION"),                        # EC-L-04
    ({"params": {"start_date": "2026-1-1"}}, "REQ_BAD_PARAM"),                          # EC-L-08 not YYYY-MM-DD
    ({"params": {"start_date": "2026-02-30"}}, "REQ_BAD_PARAM"),                        # EC-L-08 impossible date
    ({"params": {"start_date": "2026-01-01; DROP TABLE message"}}, "REQ_BAD_PARAM"),    # EC-L-07 typed before it travels
    ({"params": {"start_date": 20260101}}, "REQ_BAD_PARAM"),
    ({"params": {"start_date": "20260101"}}, "REQ_BAD_PARAM"),                        # basic ISO form is not the contract
    ({"params": {"ghost": "x"}}, "REQ_UNKNOWN_PARAM"),
    ({"where": [{"dim": "market", "in": []}]}, "REQ_BAD_WHERE"),                        # EC-L-22 empty IN
    ({"where": [{"dim": "market", "in": ["HK", None]}]}, "REQ_NULL_IN_FILTER"),         # EC-L-22 NULL never matches
    ({"where": [{"dim": "market", "eq": None}]}, "REQ_NULL_IN_FILTER"),
    ({"where": [{"dim": "ghost", "eq": "x"}]}, "REQ_UNKNOWN_DIMENSION"),
    ({"where": [{"dim": "market", "like": "H%"}]}, "REQ_BAD_WHERE"),
    ({"where": [{"dim": "market", "in": [["nested"]]}]}, "REQ_BAD_WHERE"),
    ({"model_version": "deadbeef0000"}, "REQ_VERSION_MISMATCH"),                       # EC-L-29
    ({"kpis": ["reached"], "published": True}, "REQ_UNCONFIRMED_KPI"),                 # EC-L-16
    ({"surprise": 1}, "REQ_UNKNOWN_FIELD"),
])
def test_invalid_requests_name_their_reason(model, fields, expected):
    assert check(model, **fields) == expected


def test_too_many_dimensions_is_refused(model):
    """EC-L-12: more dimensions than a report; a cube request is a different product."""
    from edgekpi import Dimension, SemanticModel
    wide = SemanticModel("w", "t", "id", model.measures, model.kpis[:1], tuple(Dimension(f"d{i}", f"c{i}") for i in range(9)))
    with pytest.raises(RequestError) as caught:
        validate(wide, ReportRequest(kpis=("sent",), rows=tuple(f"d{i}" for i in range(9))))
    assert caught.value.code == "REQ_TOO_MANY_DIMENSIONS"


def test_the_pinned_version_passes_and_unconfirmed_kpis_pass_when_not_published(model):
    validate(model, ReportRequest(kpis=("sent",), model_version=model.fingerprint()))
    validate(model, ReportRequest(kpis=("reached",)))
    validate(model, ReportRequest(kpis=("sent",), published=True))


def test_optional_filters_skip_when_unset_and_missing_required_ones_fail(model):
    report = validate(model, ReportRequest(kpis=("sent",)))
    assert all(f.skipped for f in report.filters)
    report = validate(model, ReportRequest(kpis=("sent",), params={"start_date": datetime.date(2026, 1, 1)}))
    assert [f.skipped for f in report.filters] == [False, True]
    assert report.bindings["start_date"].value == "2026-01-01"


def test_a_required_filter_without_its_parameter_fails_and_a_partial_optional_one_too():
    from edgekpi import Filter, Kpi, Measure, Param, SemanticModel
    base = dict(name="m", source="t", key="id", measures=(Measure("n", "COUNT(*)"),), kpis=(Kpi("k", "n"),))
    required = SemanticModel(**base, filters=(Filter("f", "CAST(d AS DATE) >= :a", (Param("a", "date"),)),))
    with pytest.raises(RequestError) as missing:
        validate(required, ReportRequest(kpis=("k",)))
    assert missing.value.code == "REQ_MISSING_PARAM"
    two = SemanticModel(**base, filters=(Filter("f", "d >= :a AND d < :b", (Param("a", "int"), Param("b", "int")), optional=True),))
    with pytest.raises(RequestError) as partial:
        validate(two, ReportRequest(kpis=("k",), params={"a": 1}))
    assert partial.value.code == "REQ_PARTIAL_PARAMS"


@pytest.mark.parametrize("rows, cols, rt, ct, expected", [
    (("a", "b"), ("c",), True, True, [("a", "b", "c"), ("a", "b"), ("a", "c"), ("a",), ("c",), ()]),
    (("a",), ("c",), False, False, [("a", "c")]),
    (("a",), ("c",), True, False, [("a", "c"), ("c",)]),
    ((), (), True, True, [()]),                                                         # EC-L-26
])
def test_the_lattice_is_the_cross_product_of_two_rollups(rows, cols, rt, ct, expected):
    assert sorted(lattice(rows, cols, rt, ct)) == sorted(expected)


def test_grouping_id_round_trips_and_follows_the_sql_bit_order():
    dims = ("a", "b", "c")
    for scope in lattice(("a", "b"), ("c",)):
        assert scope_of(gid(scope, dims), dims) == scope
    assert gid(("a", "b", "c"), dims) == 0 and gid((), dims) == 7 and gid(("a", "b"), dims) == 1 and gid(("a",), dims) == 3


def test_scope_count_is_the_product_of_axis_levels():
    assert len(axis_levels(("a", "b", "c"), True)) == 4
    assert len(lattice(("a", "b", "c"), ("d", "e"), True, True)) == 4 * 3
