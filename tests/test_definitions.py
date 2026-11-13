"""The semantic model refuses what it cannot guarantee. EC-L-05 EC-L-06 EC-L-07 EC-L-10 EC-L-27 EC-L-32"""
import json

import pytest
from conftest import MODEL_PATH

from edgekpi import DefinitionError, dumps, load, loads

BASE = """
name: m
source: t
key: id
measures:
  n: COUNT(*)
"""


def build(extra: str = "", base: str = BASE):
    return loads(base + extra)


def code(text: str, base: str = BASE) -> str:
    with pytest.raises(DefinitionError) as caught:
        loads(base + text)
    return caught.value.code


def test_the_example_model_round_trips_through_yaml():
    model = load(MODEL_PATH)
    assert loads(dumps(model)) == model


def test_measure_kinds_are_read_from_the_aggregate_not_declared():
    model = load(MODEL_PATH)
    assert {m.name: m.kind for m in model.measures} == {
        "n_sent": "count", "n_delivered": "count", "n_opened": "count", "n_clicked": "count", "n_reached": "unique"}
    assert not model.measure("n_reached").additive and model.measure("n_sent").additive


@pytest.mark.parametrize("expression, expected", [
    ("(SELECT 1)", "DEF_NOT_AN_AGGREGATE"),                            # EC-L-10 subquery
    ("SUM(x) OVER (PARTITION BY y)", "DEF_NOT_AN_AGGREGATE"),          # EC-L-10 window
    ("SUM(COUNT(*))", "DEF_NESTED_AGGREGATE"),                         # EC-L-10 nested aggregate
    ("my_udf(x)", "DEF_NOT_AN_AGGREGATE"),                             # EC-L-10 unknown function
    ("COUNT(*) / COUNT(x)", "DEF_NOT_AN_AGGREGATE"),                   # ratios belong to KPIs
    ("SUM((SELECT 1))", "DEF_UNSUPPORTED_CONSTRUCT"),                  # EC-L-10 subquery inside an aggregate
    ("COUNT(*", "DEF_SYNTAX"),
    ("", "DEF_EMPTY_EXPRESSION"),
])
def test_unsafe_or_unsupported_measures_are_refused_with_a_reason(expression, expected):
    assert code(f"  bad: {json.dumps(expression)}\n") == expected


@pytest.mark.parametrize("name", ["a b", "1x", "x;drop", "x-y", "a.b", "é"])
def test_names_that_could_carry_sql_are_refused(name):
    """EC-L-07: identifiers are checked against [A-Za-z_][A-Za-z0-9_]*; they are the only text copied into SQL."""
    assert code(f"  {json.dumps(name)}: COUNT(*)\n") == "DEF_BAD_IDENTIFIER"


def test_a_malicious_source_name_is_refused():
    assert code("", base=BASE.replace("source: t", 'source: "t; DROP TABLE x"')) == "DEF_BAD_IDENTIFIER"


@pytest.mark.parametrize("extra, expected", [
    ("kpis:\n  k: {formula: ghost}\n", "DEF_UNKNOWN_MEASURE"),                          # EC-L-05/06
    ("kpis:\n  k: {formula: ratio(n)}\n", "DEF_BAD_RATIO"),                              # EC-L-06
    ("kpis:\n  k: {formula: n.x}\n", "DEF_QUALIFIED_REFERENCE"),                         # EC-L-06
    ("kpis:\n  k: {formula: \"n + (SELECT 1)\"}\n", "DEF_UNSUPPORTED_CONSTRUCT"),
    ("kpis:\n  n: {formula: n}\n", "DEF_DUPLICATE_NAME"),                               # EC-L-27 measure and KPI share a name
    ("dimensions:\n  n: x\n", "DEF_DUPLICATE_NAME"),                                     # EC-L-27
    ("dimensions:\n  gid: x\n", "DEF_RESERVED_NAME"),                                    # EC-L-27 collides with the grouping id
    ("dimensions:\n  edgekpi_rows: x\n", "DEF_RESERVED_NAME"),
    ("dimensions:\n  d: ghost.x\n", "DEF_UNKNOWN_QUALIFIER"),
    ("kpis:\n  k: {formula: n, status: shipped}\n", "DEF_BAD_STATUS"),
    ("joins:\n  j: {table: u, on: 'id = j.id', cardinality: many}\n", "DEF_JOIN_CARDINALITY"),
    ("joins:\n  source: {table: u, on: 'id = source.id'}\n", "DEF_RESERVED_NAME"),
    ("filters:\n  f: {predicate: 'x > :p', params: {q: date}}\n", "DEF_PARAM_MISMATCH"),
    ("filters:\n  f: {predicate: 'x > 1', optional: true}\n", "DEF_PARAM_MISMATCH"),
    ("filters:\n  f: {predicate: 'x > :p', params: {p: blob}}\n", "DEF_BAD_PARAM_TYPE"),
    ("filters:\n  f: {predicate: 'COUNT(*) > :p', params: {p: int}}\n", "DEF_UNSUPPORTED_CONSTRUCT"),
    ("surprise: 1\n", "DEF_UNKNOWN_FIELD"),                                              # EC-L-32 unknown fields fail closed
    ("kpis:\n  k: {formula: n, colour: red}\n", "DEF_UNKNOWN_FIELD"),
])
def test_invalid_definitions_name_their_reason(extra, expected):
    assert code(extra) == expected


def test_yaml_on_key_is_not_read_as_a_boolean():
    """EC-L-32: YAML 1.1 turns `on:` into True. The loader keeps it as the string a join needs."""
    model = build("joins:\n  j: {table: u, on: 'id = j.id'}\n")
    assert model.joins[0].on == "id = j.id"


def test_a_model_needs_a_measure_and_valid_yaml():
    with pytest.raises(DefinitionError) as no_measure:
        loads("name: m\nsource: t\nkey: id\n")
    assert no_measure.value.code == "DEF_NO_MEASURES"
    assert code("", base="name: m\nsource: t\nkey: id\nmeasures: [") == "DEF_YAML"


def test_the_fingerprint_changes_with_any_definition_change():
    """EC-L-29 depends on it: a reviewed model has an identity."""
    a = build("kpis:\n  k: {formula: n}\n")
    b = build("kpis:\n  k: {formula: 'n * 2'}\n")
    assert a.fingerprint() != b.fingerprint() and a.fingerprint() == build("kpis:\n  k: {formula: n}\n").fingerprint()
