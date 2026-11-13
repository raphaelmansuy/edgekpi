"""The demo server Cloud Run runs: the built front end and the API on one port."""
import http.client
import importlib.util
import json
import pathlib
import threading
import urllib.error
import urllib.request

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROUTES = ("catalogue", "evidence", "inference", "messages", "plan", "run", "explain", "verify", "resolve")


def load_serve():
    spec = importlib.util.spec_from_file_location("edgekpi_demo_serve", ROOT / "demo" / "serve.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stub_service():
    """Routes are stored, not called: an unknown API path answers 404 before it touches the service."""
    return type("Stub", (), {name: None for name in ROUTES})()


@pytest.fixture
def demo(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>edgekpi demo</title>")
    (dist / "assets" / "x.js").write_text("console.log('ok')")
    (tmp_path / "secret.txt").write_text("nope")

    serve = load_serve()
    server = serve.ThreadingHTTPServer(("127.0.0.1", 0), serve.make_demo_handler(stub_service(), dist))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    def call(path):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.headers, error.read()

    call.port = port
    yield call
    server.shutdown()
    server.server_close()


def test_the_front_page_is_index_html(demo):
    status, headers, body = demo("/")
    assert status == 200 and b"edgekpi demo" in body
    assert headers["Content-Type"].startswith("text/html") and headers["Cache-Control"] == "no-cache"


def test_a_built_asset_is_served(demo):
    status, headers, body = demo("/assets/x.js")
    assert status == 200 and body == b"console.log('ok')"
    assert "immutable" in headers["Cache-Control"]


def test_an_unknown_path_is_the_app(demo):
    status, _, body = demo("/no/such/screen")
    assert status == 200 and b"edgekpi demo" in body


def test_an_unknown_api_route_stays_a_404(demo):
    status, _, body = demo("/api/missing")
    assert status == 404 and json.loads(body)["error"]["code"] == "NOT_FOUND"


def test_health_answers_ok(demo):
    status, _, body = demo("/health")
    assert status == 200 and json.loads(body) == {"ok": True}


@pytest.mark.parametrize("path", ["/../secret.txt", "/assets/../../secret.txt", "/%2e%2e/secret.txt"])
def test_a_path_that_leaves_dist_is_not_served(demo, path):
    connection = http.client.HTTPConnection("127.0.0.1", demo.port)
    connection.request("GET", path)
    response = connection.getresponse()
    body = response.read()
    connection.close()
    assert response.status == 200 and b"nope" not in body and b"edgekpi demo" in body


def _listen(serve, dist, cap=None):
    handler = serve.make_demo_handler(stub_service(), dist, cap)
    server = serve.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def call(path, method="GET", body=None):
        connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        connection.request(method, path, body=body, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        payload = response.read()
        connection.close()
        return response.status, payload

    call.server = server
    return call


def test_the_cap_pauses_pages_and_the_api_but_not_health(tmp_path):
    serve = load_serve()
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>edgekpi demo</title>")
    cap = serve.MonthCap(86_400, lambda: 86_400, clock=lambda: 0)
    call = _listen(serve, dist, cap)
    try:
        status, body = call("/")
        assert status == 503 and b"24 hours" in body
        status, body = call("/api/run", "POST", b"{}")
        assert status == 503 and json.loads(body)["error"]["code"] == "MONTHLY_LIMIT"
        status, body = call("/health")
        assert status == 200 and json.loads(body) == {"ok": True}
    finally:
        call.server.shutdown()
        call.server.server_close()


def test_a_failed_usage_read_leaves_the_demo_open(tmp_path):
    serve = load_serve()
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>edgekpi demo</title>")

    def fail():
        raise RuntimeError("monitoring down")

    call = _listen(serve, dist, serve.MonthCap(86_400, fail, clock=lambda: 0))
    try:
        status, body = call("/")
        assert status == 200 and b"edgekpi demo" in body
    finally:
        call.server.shutdown()
        call.server.server_close()


def test_usage_is_reread_after_the_refresh_interval():
    serve = load_serve()
    calls = {"n": 0}

    def read():
        calls["n"] += 1
        return 1

    now = {"t": 0.0}
    cap = serve.MonthCap(86_400, read, clock=lambda: now["t"], refresh=60)
    assert cap.over() is False and calls["n"] == 1
    assert cap.over() is False and calls["n"] == 1
    now["t"] = 60
    assert cap.over() is False and calls["n"] == 2


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_monitoring_seconds_sums_the_month_and_follows_pages():
    serve = load_serve()
    seen = []

    def urlopen(request, timeout=None):
        seen.append(request.full_url)
        if len(seen) == 1:
            return _Response({"timeSeries": [{"points": [{"value": {"doubleValue": 6.4}}]}], "nextPageToken": "next"})
        return _Response({"timeSeries": [{"points": [{"value": {"int64Value": "62"}}]}]})

    start = serve.datetime(2026, 11, 1, tzinfo=serve.timezone.utc)
    end = serve.datetime(2026, 11, 13, tzinfo=serve.timezone.utc)
    assert serve.monitoring_seconds(urlopen, "saas-app-001", "token", "edgekpi-demo", start, end) == 68.4
    assert "edgekpi-demo" in seen[0] and "pageToken=next" in seen[1]


def test_the_first_minute_of_a_month_is_not_queried():
    serve = load_serve()

    def urlopen(request, timeout=None):
        raise AssertionError("no query in the first minute")

    start = serve.datetime(2026, 12, 1, tzinfo=serve.timezone.utc)
    assert serve.monitoring_seconds(urlopen, "saas-app-001", "token", "edgekpi-demo", start, start) == 0


def test_main_stops_when_the_build_is_missing(monkeypatch, tmp_path):
    serve = load_serve()
    monkeypatch.setattr(serve, "DIST", tmp_path / "missing")
    with pytest.raises(SystemExit, match="demo build missing"):
        serve.main()
