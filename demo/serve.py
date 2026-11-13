"""The demo on one port: the built front end plus the API. Standard library only.

Cloud Run sets PORT and sends traffic to 0.0.0.0. Hash routes need no rewrite: a path that is not an API
call is a file under demo/web/dist, or index.html when that file is not there.

    python demo/serve.py
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from urllib.parse import unquote

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:          # `python demo/serve.py` puts demo/ on the path, not the repo root
    sys.path.insert(0, str(ROOT))

from edgekpi.server import default_service, make_handler

DIST = ROOT / "demo" / "web" / "dist"

TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".map": "application/json",
    ".txt": "text/plain; charset=utf-8",
}
IMMUTABLE = "public, max-age=31536000, immutable"
NO_CACHE = "no-cache"
METADATA = "http://metadata.google.internal/computeMetadata/v1"
BILLABLE = "run.googleapis.com/container/billable_instance_time"


def sum_seconds(payload: dict) -> float:
    """Seconds reported by a Cloud Monitoring time-series response."""
    total = 0.0
    for series in payload.get("timeSeries", []):
        for point in series.get("points", []):
            value = point.get("value", {})
            if "doubleValue" in value:
                total += float(value["doubleValue"])
            elif "int64Value" in value:
                total += float(value["int64Value"])
    return total


def monitoring_seconds(urlopen, project: str, token: str, service: str, start: datetime, end: datetime) -> float:
    """Billable Cloud Run seconds for one service since `start`. The first minute of a month counts as zero."""
    span = (end - start).total_seconds()
    if span < 60:
        return 0.0
    query = urllib.parse.urlencode({
        "filter": f'resource.type="cloud_run_revision" AND metric.type="{BILLABLE}" AND resource.labels.service_name="{service}"',
        "interval.startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "interval.endTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "aggregation.alignmentPeriod": f"{max(60, int(span))}s",
        "aggregation.perSeriesAligner": "ALIGN_SUM",
        "aggregation.crossSeriesReducer": "REDUCE_SUM",
    })
    url = f"https://monitoring.googleapis.com/v3/projects/{project}/timeSeries?{query}"
    total = 0.0
    for _ in range(5):
        payload = _get_json(urlopen, url, token)
        total += sum_seconds(payload)
        token_page = payload.get("nextPageToken")
        if not token_page:
            break
        url = f"https://monitoring.googleapis.com/v3/projects/{project}/timeSeries?{query}&pageToken={urllib.parse.quote(token_page)}"
    return total


def _get_json(urlopen, url: str, token: str) -> dict:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode() or "{}")


def _metadata(urlopen, path: str) -> str:
    request = urllib.request.Request(METADATA + "/" + path, headers={"Metadata-Flavor": "Google"})
    with urlopen(request, timeout=2) as response:
        return response.read().decode()


class CloudRunUsage:
    """Month-to-date billable time of this Cloud Run service, read from inside the container."""

    def __init__(self, urlopen=urllib.request.urlopen):
        self.urlopen = urlopen
        self.service = os.environ["K_SERVICE"]
        self.project = _metadata(urlopen, "project/project-id").strip()
        self._token = ""
        self._token_until = 0.0

    def seconds(self) -> float:
        now = datetime.now(timezone.utc)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return monitoring_seconds(self.urlopen, self.project, self.token(), self.service, start, now)

    def token(self) -> str:
        if self._token and time.monotonic() < self._token_until:
            return self._token
        payload = json.loads(_metadata(self.urlopen, "instance/service-accounts/default/token"))
        self._token = payload["access_token"]
        self._token_until = time.monotonic() + max(0, int(payload.get("expires_in", 300)) - 60)
        return self._token


class MonthCap:
    """Refuse work once billable time this UTC month reaches the limit. A failed read leaves the demo open."""

    def __init__(self, limit_seconds: int, read, clock=time.monotonic, refresh: float = 60):
        self.limit_seconds = limit_seconds
        self.read = read
        self.clock = clock
        self.refresh = refresh
        self.lock = threading.Lock()
        self.used = 0.0
        self.checked_at = None

    @property
    def message(self) -> str:
        hours = self.limit_seconds / 3600
        shown = str(int(hours)) if hours.is_integer() else f"{hours:g}"
        return f"This demo has used its {shown} hours for this month. It resumes on the 1st (UTC)."

    def over(self) -> bool:
        if self.limit_seconds <= 0:
            return False
        now = self.clock()
        with self.lock:
            if self.checked_at is None or now - self.checked_at >= self.refresh:
                try:
                    self.used = float(self.read())
                    print(f"billable this month: {self.used:.0f}s of {self.limit_seconds}s", flush=True)
                except Exception as error:
                    print(f"monthly limit check failed: {type(error).__name__} {error}", flush=True)
                self.checked_at = now
            return self.used >= self.limit_seconds


def month_cap_from_env() -> MonthCap:
    limit = int(os.environ.get("EDGEKPI_MONTHLY_SECONDS", "0") or 0)
    if limit <= 0:
        return MonthCap(0, lambda: 0.0)
    usage = CloudRunUsage()
    return MonthCap(limit, usage.seconds)


def limit_page(message: str) -> bytes:
    return (
        "<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content=\"width=device-width, initial-scale=1\">"
        f"<title>edgekpi demo is paused</title><body style=\"font-family: Georgia, serif; max-width: 36rem; margin: 4rem auto; padding: 0 1rem; color: #2B3A4A\">"
        f"<h1>This demo is paused</h1><p>{message}</p></body></html>"
    ).encode()


def static_file(dist: pathlib.Path, url_path: str) -> pathlib.Path | None:
    """A file inside dist for this URL, or None. `..`, even percent-encoded, cannot leave dist."""
    root = dist.resolve()
    relative = unquote(url_path.split("?", 1)[0]).lstrip("/")
    if not relative:
        return None
    candidate = (root / relative).resolve()
    if root not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def make_demo_handler(service, dist: pathlib.Path = DIST, cap: MonthCap | None = None):
    base = make_handler(service)
    root = pathlib.Path(dist).resolve()
    limit = cap if cap is not None else month_cap_from_env()

    class Handler(base):
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/health":
                return self._send(200, {"ok": True})          # not /healthz: Cloud Run reserves paths that end in z
            if self._paused():
                return None
            if path.startswith("/api/"):
                return super().do_GET()
            target = static_file(root, self.path)
            if target is None:
                index = root / "index.html"
                if not index.is_file():
                    return self._send(500, {"ok": False, "error": {"code": "DEMO_NOT_BUILT", "message": f"missing {index}", "states": []}})
                return self._file(index, NO_CACHE)
            cache = IMMUTABLE if path.startswith("/assets/") else NO_CACHE
            self._file(target, cache)

        def do_POST(self):
            if not self._paused():
                super().do_POST()

        def _paused(self) -> bool:
            if not limit.over():
                return False
            path = self.path.split("?", 1)[0]
            if path.startswith("/api/"):
                self._send(503, {"ok": False, "error": {"code": "MONTHLY_LIMIT", "message": limit.message, "states": []}})
            else:
                body = limit_page(limit.message)
                self.send_response(503)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            return True

        def _file(self, path: pathlib.Path, cache: str) -> None:
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", TYPES.get(path.suffix.lower(), "application/octet-stream"))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", cache)
            self.end_headers()
            self.wfile.write(data)

    return Handler


def main() -> None:
    index = DIST / "index.html"
    if not index.is_file():
        raise SystemExit(f"demo build missing: {index}. The image builds demo/web/dist.")
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), make_demo_handler(default_service(), cap=month_cap_from_env()))
    print(f"edgekpi demo on http://0.0.0.0:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
