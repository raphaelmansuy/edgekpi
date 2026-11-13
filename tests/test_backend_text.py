"""What the backends write. Text-level guarantees that do not need an engine. EC-L-07 EC-L-20 EC-L-23"""
import pytest
import yaml

from edgekpi import GeneratedSql, ReportRequest, UnsupportedError, validate
from edgekpi.backends.malloy import Malloy, literal
from edgekpi.backends.metric_view import MetricView
from edgekpi.estimate import estimate


def report(model, **fields):
    return validate(model, ReportRequest.from_dict({"kpis": ["delivery_rate"], **fields}))


def test_parameters_stay_bound_and_never_enter_the_sql_text(model):
    """EC-L-07: values travel as bindings; the text is the same whatever the values are."""
    hostile = "2026-01-01"
    a = GeneratedSql().compile(report(model, params={"start_date": hostile}))
    b = GeneratedSql().compile(report(model, params={"start_date": "2025-05-05"}))
    assert a.query.text == b.query.text and ":start_date" in a.query.text
    assert hostile not in a.query.text
    assert {x.name: x.value for x in a.query.params}["start_date"] == hostile


def test_where_values_are_bound_not_inlined(model):
    plan = GeneratedSql().compile(report(model, where=[{"dim": "market", "in": ["HK'; DROP TABLE message; --", "SG"]}]))
    assert "DROP" not in plan.query.text and ":w0_0" in plan.query.text and ":w0_1" in plan.query.text
    assert [b.value for b in plan.query.params if b.name.startswith("w0")] == ["HK'; DROP TABLE message; --", "SG"]


def test_malloy_literals_escape_quotes_backslashes_and_newlines(model):
    """EC-L-07: Malloy has no bound parameters here, so the literal renderer is the defence."""
    assert literal("a'b", "string") == "'a\\'b'"
    assert literal("a\\b", "string") == "'a\\\\b'"
    assert literal("a\nb", "string") == "'a\\nb'"
    assert literal("2026-01-01", "date") == "@2026-01-01"
    assert literal(None, "date") == "null"
    plan = Malloy().compile(report(model, where=[{"dim": "market", "eq": "x' or 1=1 or 'y"}]))
    assert "market = 'x\\' or 1=1 or \\'y'" in plan.query.text


def test_every_division_is_guarded_in_every_backend(model):
    """EC-L-23: Malloy returns NaN for an unguarded division and Databricks ANSI mode raises; none may be written bare."""
    r = report(model)
    assert "NULLIF(n_sent, 0)" in GeneratedSql().compile(r).query.text
    assert "nullif(n_sent, 0)" in Malloy().compile(r).query.text
    mv = MetricView().ddl(model)
    assert "NULLIF(MEASURE(n_sent), 0)" in mv


def test_measures_behind_several_kpis_are_computed_once(model):
    """EC-L-20: open and click rate both divide by delivered; the aggregate appears once."""
    text = GeneratedSql().compile(report(model).__class__(**{**report(model).__dict__, "kpis": tuple(model.kpi(k) for k in ("open_rate", "click_rate")),
                                                              "atoms": tuple(model.atoms_of(["open_rate", "click_rate"]))})).query.text
    assert text.count("AS n_delivered") == 1


def test_the_metric_view_is_one_definition_per_model_version(model):
    backend = MetricView("main", "kpi")
    assert backend.view_name(model) == f"main.kpi.edgekpi_engagement_{model.fingerprint()}"
    ddl = backend.ddl(model)
    assert ddl.startswith("CREATE OR REPLACE VIEW main.kpi.edgekpi_engagement_") and "WITH METRICS LANGUAGE YAML" in ddl
    body = yaml.safe_load(ddl.split("$$\n")[1].removesuffix("$$"))
    assert body["version"] == 1.1 and body["source"] == "message"
    assert body["joins"] == [{"name": "client", "source": "client", "on": "source.client_id = client.client_id"}]
    measures = {m["name"]: m["expr"] for m in body["measures"]}
    assert measures["delivery_rate"] == "MEASURE(n_delivered) * 1.0 / NULLIF(MEASURE(n_sent), 0)"
    assert measures["edgekpi_rows"] == "COUNT(*)"
    names = [d["name"] for d in body["dimensions"]]
    assert "market" in names and "edgekpi_col_source_send_date" in names       # filters read hidden dimensions


def test_metric_view_filters_read_dimensions_not_raw_columns(model):
    text = MetricView().compile(report(model, params={"start_date": "2026-01-01"})).query.text
    assert "CAST(edgekpi_col_source_send_date AS DATE)" in text and "source." not in text


def test_the_grouping_sets_are_the_requested_lattice(model):
    text = GeneratedSql().compile(report(model, rows=["typology"], cols=["market"])).query.text
    assert "GROUP BY GROUPING SETS ((client.typology, source.market), (client.typology), (source.market), ())" in text
    assert "GROUPING_ID(client.typology, source.market) AS gid" in text


def test_a_construct_malloy_cannot_express_is_refused_by_name():
    from edgekpi import loads
    model = loads("name: m\nsource: t\nkey: id\ndimensions:\n  d: \"CASE x WHEN 1 THEN 'a' END\"\nmeasures:\n  n: COUNT(*)\nkpis:\n  k: n\n")
    with pytest.raises(UnsupportedError) as caught:
        Malloy().compile(validate(model, ReportRequest(kpis=("k",), rows=("d",))))
    assert caught.value.code == "MALLOY_UNSUPPORTED" and caught.value.detail["construct"] == "Case"


def test_count_of_a_column_is_not_confused_with_a_distinct_count_in_malloy():
    """EC-L-31: Malloy's count(x) is COUNT(DISTINCT x); SQL COUNT(x) counts non-null values. The translator keeps both meanings."""
    from edgekpi import loads
    model = loads("name: m\nsource: t\nkey: id\nmeasures:\n  filled: COUNT(x)\n  kinds: COUNT(DISTINCT x)\nkpis:\n  a: filled\n  b: kinds\n")
    source = Malloy().source(model)
    assert "filled is count() { where: x is not null }" in source and "kinds is count(x)" in source


def test_the_malloy_translator_keeps_the_meaning_of_boolean_logic():
    """A wrong connective would silently change which rows a KPI counts."""
    from edgekpi import loads
    model = loads(
        "name: m\nsource: t\nkey: id\ndimensions:\n  d: x\n"
        "measures:\n  n: COUNT(*) FILTER (WHERE a > 1 AND b IS NOT NULL OR NOT c)\n  m: COUNT(*) FILTER (WHERE x IN ('p', 'q') AND y BETWEEN 1 AND 5)\n"
        "  k: SUM(CASE WHEN a = 1 THEN 2 ELSE 3 END)\nkpis:\n  a: n\n  b: m\n  c: k\n")
    source = Malloy().source(model)
    assert "n is count() { where: a > 1 and b is not null or not c }" in source
    assert "m is count() { where: (x = 'p' or x = 'q') and (y >= 1 and y <= 5) }" in source
    assert "k is sum(pick 2 when a = 1 else 3)" in source


def test_malloy_tables_can_be_qualified_for_a_warehouse(model):
    source = Malloy(connection="databricks", table_prefix="workspace.edgekpi_lib.").source(model)
    assert "source: engagement is databricks.table('workspace.edgekpi_lib.message') extend {" in source
    assert "join_one: client is databricks.table('workspace.edgekpi_lib.client') on client_id = client.client_id" in source


@pytest.mark.malloy
def test_the_warehouse_token_reaches_node_through_the_environment_only():
    """The token must not appear in the payload (stdin), which could be logged or echoed in an error."""
    import json
    from types import SimpleNamespace

    from edgekpi.engines.malloy import MalloyDatabricksEngine

    client = SimpleNamespace(
        config=SimpleNamespace(host="https://example.cloud.databricks.com", authenticate=lambda: {"Authorization": "Bearer SECRET-TOKEN"}),
        warehouses=SimpleNamespace(get=lambda _id: SimpleNamespace(odbc_params=SimpleNamespace(path="/sql/1.0/warehouses/abc"))),
    )
    engine = MalloyDatabricksEngine(SimpleNamespace(client=client, warehouse="abc", catalog="c", schema="s"))
    payload = engine._payload()
    assert "SECRET-TOKEN" not in json.dumps(payload) and payload["databricks"]["host"] == "example.cloud.databricks.com"
    assert payload["databricks"]["path"] == "/sql/1.0/warehouses/abc" and engine.table_prefix == "c.s."
    assert engine._environment()["EDGEKPI_DBX_TOKEN"] == "SECRET-TOKEN"


def test_the_estimate_is_arithmetic_on_the_request(model):
    e = estimate(report(model, rows=["typology", "tier"], cols=["market"]))
    assert (e.scopes, e.measures, e.distinct_measures, e.aggregate_states) == (6, 2, 0, 12)
    assert "6 scopes" in e.description
