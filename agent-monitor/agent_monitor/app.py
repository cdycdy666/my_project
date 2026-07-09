from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .collector import collect_architecture, collect_run_detail, collect_runs, collect_summary


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = PROJECT_ROOT / "static"


class MonitorHandler(BaseHTTPRequestHandler):
    server_version = "AgentMonitor/0.1"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            self._send_json({"ok": True})
            return
        if path == "/":
            self._send_file(STATIC_ROOT / "index.html")
            return
        if path.startswith("/static/"):
            self._send_file(STATIC_ROOT / path.removeprefix("/static/"))
            return
        if path == "/api/summary":
            self._send_json(collect_summary())
            return
        if path == "/api/architecture":
            self._send_json(collect_architecture())
            return
        if path == "/api/runs":
            params = parse_qs(parsed.query)
            agent = (params.get("agent") or [None])[0]
            limit = int((params.get("limit") or ["200"])[0])
            self._send_json({"runs": collect_runs(agent_id=agent, limit=limit, include_events=False)})
            return
        if path.startswith("/api/runs/"):
            trace_id = unquote(path.removeprefix("/api/runs/"))
            detail = collect_run_detail(trace_id)
            if detail:
                self._send_json(detail)
            else:
                self._send_json({"error": "run not found", "trace_id": trace_id}, status=404)
            return
        self._send_json({"error": "not found"}, status=404)

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib hook
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/api/health"}:
            self.send_response(200)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def _send_json(self, payload: object, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file() or STATIC_ROOT not in path.resolve().parents and path.resolve() != STATIC_ROOT:
            self._send_json({"error": "file not found"}, status=404)
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        raw = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def run() -> None:
    host = os.environ.get("AGENT_MONITOR_HOST", "127.0.0.1")
    port = int(os.environ.get("AGENT_MONITOR_PORT", "8769"))
    server = ThreadingHTTPServer((host, port), MonitorHandler)
    print(f"Agent Monitor listening on http://{host}:{port}")
    server.serve_forever()
