"""The service layer and its HTTP wrapper: what the demo's screens depend on. EC-D-05 EC-D-06 EC-D-11 EC-D-22 EC-D-23 EC-D-24"""
import http.client as httpclient
import json
import threading
import urllib.error
import urllib.request

import pytest
from conftest import EXAMPLES, MODEL_PATH, REQUESTS

from edgekpi import GeneratedSql, ReportRequest, RequestError, run, validate
from edgekpi.explain import explain
from edgekpi.server import LEGACY, make_handler, serve
from edgekpi.service import Service, error_payload

EVIDENCE = sorted((MODEL_PATH.parents[2] / "specs" / "library" / "evidence").glob("run-*-databricks.json"))


@pytest.fixture(scope="module")
def service():
    return Service(MODEL_PATH, EXAMPLES / "data.sql", EXAMPLES / "templates.sql", EVIDENCE[-1] if EVIDENCE else None, LEGACY)


@pytest.fixture(scope="module")
def http(service):
    server = serve(service, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    def call(path, body=None, raw=None):
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
        request = urllib.request.Request(base + path, data=data, method="POST" if data is not None else "GET", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    call.host, call.port = "127.0.0.1", server.server_address[1]
    yield call
    server.shutdown()


def test_the_catalogue_describes_the_model_and_proves_its_grain(service):
    c = service.catalogue()
    assert c["ok"] and c["grain"] == {"fact_rows": 13, "joined_rows": 13, "distinct_keys": 13}
    assert [k["id"] for k in c["kpis"]][:2] == ["sent", "reached"] and c["measures"][-1] == {"id": "n_reached", "expr": "COUNT(DISTINCT client_id) FILTER (WHERE is_delivered)", "kind": "unique", "additive": False}
    assert {b["id"]: b["available"] for b in c["backends"]}["sql"] and not {b["id"]: b["available"] for b in c["backends"]}["metric-view"]
    assert c["schema"]["properties"]["kpis"]["items"]["enum"][0] == "sent"


def test_run_returns_long_form_nodes_the_ui_can_pivot(service):
    out = service.run(REQUESTS["two-row-levels"])
    assert out["ok"] and out["states"][-1] == "RECONCILED" and out["violations"] == []
    scopes = {tuple(n["scope"]) for n in out["nodes"]}
    assert () in scopes and ("typology", "tier", "market") in scopes
    none_member = [n for n in out["nodes"] if n["scope"] == ["typology"] and n["members"] == [None]]
    assert len(none_member) == 1, "EC-D-05: a NULL member is a node of its own, distinct from the total"


def test_domain_errors_carry_a_code_and_a_status(service, http):
    status, body = http("/api/run", {"request": {"kpis": ["ghost"]}, "backend": "sql"})
    assert status == 422 and body["error"]["code"] == "REQ_UNKNOWN_KPI" and body["ok"] is False
    status, body = http("/api/run", {"request": {"kpis": ["sent"]}, "backend": "metric-view"})
    assert status == 501 and body["error"]["code"] == "ENGINE_UNAVAILABLE", "EC-D-06: an unavailable backend is said so, not faked"
    status, body = http("/api/run", {"request": {"kpis": ["sent"]}, "backend": "nope"})
    assert status == 422 and body["error"]["code"] == "REQ_UNKNOWN_BACKEND"


def test_a_metric_view_plan_can_be_shown_without_a_warehouse(service):
    out = service.plan({"kpis": ["sent"], "rows": ["market"]}, "metric-view")
    assert [s["kind"] for s in out["statements"]] == ["ddl", "query"] and "WITH METRICS" in out["statements"][0]["text"]


def test_the_same_malloy_model_is_written_for_duckdb_and_for_databricks(service):
    """EC-D-30: only the connection and the table paths differ; the measures, formulas and nests are the same text."""
    request = {"kpis": ["delivery_rate"], "rows": ["typology"], "cols": ["market"]}
    duck = service.plan(request, "malloy")
    explicit = service.plan(request, "malloy", "duckdb")
    dbx = service.plan(request, "malloy", "databricks")
    assert duck["statements"] == explicit["statements"] and duck["connection"]["engine"] == "duckdb"
    d, b = duck["statements"][0]["text"], dbx["statements"][0]["text"]
    assert "duckdb.table('message')" in d and "databricks.table('workspace.edgekpi_lib.message')" in b
    assert "databricks.table('workspace.edgekpi_lib.client')" in b
    assert d.replace("duckdb.table('", "databricks.table('workspace.edgekpi_lib.") == b
    assert "DatabricksConnection" in dbx["connection"]["text"] and "process.env.EDGEKPI_DBX_TOKEN" in dbx["connection"]["text"]
    assert "dapi" not in dbx["connection"]["text"] and "<warehouse-id>" in dbx["connection"]["text"]


def test_an_engine_is_chosen_only_for_malloy_and_only_among_the_known(service):
    """EC-D-30."""
    for backend, engine in (("sql", "duckdb"), ("malloy", "oracle")):
        with pytest.raises(RequestError):
            service.plan({"kpis": ["sent"]}, backend, engine)
    assert service.plan({"kpis": ["sent"]}, "sql")["connection"] is None


def test_the_databricks_table_path_comes_from_the_recorded_run_or_a_stated_default(service):
    bare = Service(MODEL_PATH, EXAMPLES / "data.sql")
    text = bare.plan({"kpis": ["sent"]}, "malloy", "databricks")["statements"][0]["text"]
    assert "databricks.table('workspace.edgekpi_lib.message')" in text


def test_malformed_input_is_a_400_not_a_crash(http):
    """EC-D-22."""
    assert http("/api/run", raw=b"not json")[0] == 400
    assert http("/api/run", {"backend": "sql"})[0] == 400                 # no request field
    assert http("/api/run", {"request": "nope"})[0] in (400, 422)
    assert http("/api/missing")[0] == 404 and http("/api/missing", {})[0] == 404
    assert http("/api/run", raw=b"x" * 10, body=None)[0] == 400


def test_an_oversized_body_is_refused(http):
    """EC-D-22."""
    call = http
    # only the declared length is inspected: the server answers before reading the body
    conn = httpclient.HTTPConnection(call.host, call.port, timeout=5)
    conn.request("POST", "/api/run", headers={"Content-Length": "5000000", "Content-Type": "application/json"})
    assert conn.getresponse().status == 413


def test_explain_shows_the_measures_and_the_tempting_wrong_answer(service):
    out = service.explain(REQUESTS["pivot-with-params-and-where"], "delivery_rate", [], [])
    assert out["ok"] and out["is_ratio"] and out["formula"] == "ratio(n_delivered, n_sent)"
    assert {t["measure"]: t["value"] for t in out["terms"]} == {"n_delivered": 8, "n_sent": 10}
    assert out["value"] == 0.8 and out["naive"]["method"] == "mean" and out["naive"]["differs"] is True


def test_explain_a_distinct_count_shows_that_the_parts_do_not_add_up(service):
    out = service.explain(REQUESTS["pivot-with-params-and-where"], "reached", [], [])
    assert out["naive"]["method"] == "sum" and out["naive"]["value"] > out["value"]


def test_explain_a_leaf_has_nothing_to_compare(service):
    out = service.explain(REQUESTS["pivot-with-params-and-where"], "sent", ["typology", "market"], ["New", "HK"])
    assert out["naive"] is None and out["value"] == 3


def test_explain_refuses_an_unknown_node_or_kpi(service):
    with pytest.raises(RequestError) as caught:
        service.explain(REQUESTS["pivot-with-params-and-where"], "sent", ["typology"], ["Nobody"])
    assert caught.value.code == "REQ_UNKNOWN_NODE"
    with pytest.raises(RequestError):
        service.explain(REQUESTS["grand-total-only"], "ctor", [], [])         # a KPI that is not in this result


def test_verify_reports_each_backend_and_what_was_skipped(service):
    out = service.verify(REQUESTS["pivot-with-params-and-where"])
    assert out["ok"] and out["outcomes"][0]["label"] == "DuckDB" and all(o["ok"] for o in out["outcomes"])
    assert [s["id"] for s in out["skipped"]] == ["metric-view"]


def test_the_assistant_resolver_is_served(service):
    out = service.resolve({"kpis": ["Delivery Rate"], "rows": ["markt"]})
    assert out["request"]["rows"] == ["market"] and out["questions"] == [] and out["notes"]
    out = service.resolve({"kpis": ["rate"]})
    assert out["request"] is None and "which KPI" in out["questions"][0]


def test_the_inference_payload_carries_the_parity_proof(service):
    out = service.inference()
    assert out["parity"] == {"bindings": 3, "nodes": 34, "compared": 200, "nulls": 18, "different": 0, "only_after": 4}
    assert [t["accepted"] for t in out["templates"]].count(False) == 2 and all(k["status"] == "draft" for k in out["kpis"])
    assert out["yaml"].startswith("name: registry")


def test_the_raw_messages_are_served_for_the_tutorial(service):
    """EC-D-26: the tutorial shows the rows a total is made of, including the one with an unknown typology."""
    out = service.messages()
    assert out["ok"] and len(out["rows"]) == 13
    assert [r["message_id"] for r in out["rows"]] == list(range(1, 14))
    unknown = [r for r in out["rows"] if r["typology"] is None]
    assert [r["message_id"] for r in unknown] == [13] and unknown[0]["client_id"] == "c9"
    assert sum(r["is_delivered"] for r in out["rows"]) == 10


def test_a_service_without_evidence_or_templates_says_so(service):
    """EC-D-23, EC-D-24: the screens render an honest empty state, not an empty grid."""
    bare = Service(MODEL_PATH, EXAMPLES / "data.sql")
    assert bare.evidence() == {"ok": True, "available": False} and bare.inference() == {"ok": True, "available": False}


def test_the_recorded_warehouse_run_is_served_when_present(service):
    out = service.evidence()
    assert out["ok"] and (not out["available"] or (out["failed"] == 0 and "metric view on databricks" in out["pairs"]))


def test_error_payload_never_leaks_internal_details():
    status, body = error_payload(RuntimeError("secret path /etc/passwd"))
    assert status == 500 and "secret" not in json.dumps(body)


def test_run_in_the_service_equals_run_in_the_library(service):
    out = service.run(REQUESTS["grand-total-only"])
    direct = run(service.model, ReportRequest.from_dict(REQUESTS["grand-total-only"]), GeneratedSql(), service.duck)
    assert out["nodes"][0]["values"]["sent"] == direct.grid.get(())["sent"] and validate(service.model, ReportRequest.from_dict(REQUESTS["grand-total-only"]))
    assert explain(direct.report, direct.grid, "sent", (), ())["value"] == 13
