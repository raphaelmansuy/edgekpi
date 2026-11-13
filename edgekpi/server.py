"""HTTP wrapper around the service: routing and JSON, nothing else. Standard library only.

    python -m edgekpi.server --port 8765
"""
from __future__ import annotations

import argparse
import json
import pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .errors import KpiError
from .service import Service, error_payload

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAX_BODY = 1_000_000
LEGACY = {"typology": "D.typology", "market": "C.market"}


def default_service() -> Service:
    examples = ROOT / "examples" / "registry"
    evidence = sorted((ROOT / "specs" / "library" / "evidence").glob("run-*-databricks.json"))
    return Service(ROOT / "examples" / "registry" / "model.yaml", examples / "data.sql", examples / "templates.sql",
                   evidence[-1] if evidence else None, LEGACY)


def make_handler(service: Service):
    gets = {"/api/catalogue": service.catalogue, "/api/evidence": service.evidence, "/api/inference": service.inference, "/api/messages": service.messages}
    posts = {
        "/api/plan": lambda b: service.plan(b["request"], b.get("backend", "sql"), b.get("engine")),
        "/api/run": lambda b: service.run(b["request"], b.get("backend", "sql")),
        "/api/explain": lambda b: service.explain(b["request"], b["kpi"], b["scope"], b["members"], b.get("backend", "sql")),
        "/api/verify": lambda b: service.verify(b["request"]),
        "/api/resolve": lambda b: service.resolve(b["proposal"]),
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):          # quiet: tests and the demo print their own results
            pass

        def _send(self, status: int, body: dict[str, Any]):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _guard(self, action):
            try:
                self._send(200, action())
            except KpiError as error:
                self._send(*error_payload(error))
            except (KeyError, TypeError, ValueError) as error:
                self._send(400, {"ok": False, "error": {"code": "BAD_REQUEST", "message": f"malformed request: {type(error).__name__} {error}", "states": []}})
            except Exception as error:  # noqa: BLE001 - the server must answer, never crash
                self._send(*error_payload(error))

        def do_GET(self):
            route = gets.get(self.path.split("?")[0])
            if route is None:
                return self._send(404, {"ok": False, "error": {"code": "NOT_FOUND", "message": self.path, "states": []}})
            self._guard(route)

        def do_POST(self):
            route = posts.get(self.path.split("?")[0])
            if route is None:
                return self._send(404, {"ok": False, "error": {"code": "NOT_FOUND", "message": self.path, "states": []}})
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._send(413, {"ok": False, "error": {"code": "BODY_TOO_LARGE", "message": f"more than {MAX_BODY} bytes", "states": []}})
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._send(400, {"ok": False, "error": {"code": "BAD_REQUEST", "message": "the body is not JSON", "states": []}})
            self._guard(lambda: route(body))

    return Handler


def serve(service: Service, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(service))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    server = serve(default_service(), args.host, args.port)
    print(f"edgekpi service on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
