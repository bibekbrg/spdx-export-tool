"""Local web preview (PRD stretch goal: interactive HTML report preview).

Run:  spdx-export-web          (or: python -m spdx_export.web)
Opens http://127.0.0.1:8000 - upload a scan or pick a sample, see the SPDX
result, package tree, gap report and raw JSON, and download the file.

Uses only the Python standard library. Listens on this computer only (127.0.0.1).
"""

import argparse
import json
import os
import sys
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path

from . import __version__
from .adapters import file_sha256, load_scan
from .benchmark import TARGET_SECONDS, make_scan
from .benchmark import run as run_benchmark
from .mapper import build_document
from .model import ERROR, INFO, WARNING
from .serializer import to_json
from .validator import validate

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
SAMPLES_DIR = Path(os.environ.get("SPDX_SAMPLES_DIR") or Path(__file__).resolve().parents[2] / "samples")
SAMPLES = {
    "valid_scan.json": "Valid JSON",
    "valid_scan.csv": "Valid CSV",
    "missing_fields_scan.json": "Missing fields",
    "broken_scan.json": "Broken file",
}


def analyze(path: Path, display_name: str) -> dict:
    """Run the real pipeline on one file and return everything the page shows."""
    scan = load_scan(path)  # raises ValueError for unsupported file types
    diagnostics = list(scan.diagnostics)
    document, failed_stage = None, None

    if scan.has_errors:
        failed_stage = "input"
    else:
        document, map_diags = build_document(
            scan, fallback_name=Path(display_name).stem, input_digest=file_sha256(path))
        diagnostics += map_diags
        if any(d.severity == ERROR for d in map_diags):
            failed_stage, document = "mapping", None
        else:
            schema_errors = validate(document)
            if schema_errors:
                diagnostics += schema_errors
                failed_stage, document = "schema", None

    return {
        "input": display_name,
        "ok": failed_stage is None,
        "failed_stage": failed_stage,
        "counts": {
            "packages": len(scan.packages),
            "files": len(scan.files),
            "relationships": len(scan.relationships),
        },
        "gaps": {s: sum(d.severity == s for d in diagnostics) for s in (ERROR, WARNING, INFO)},
        "diagnostics": [vars(d) for d in diagnostics],
        "document": document,
        "spdx_text": to_json(document) if document else None,
    }


def speed_test(packages: int = 50, files_per_package: int = 20) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "speed_test.json"
        src.write_text(json.dumps(make_scan(packages, files_per_package)), encoding="utf-8")
        result = run_benchmark(src, Path(tmp) / "out.spdx.json")
    steps = {k: round(v, 4) for k, v in result.items() if not k.startswith("_") and k != "total"}
    return {
        "packages": result["_packages"],
        "files": result["_files"],
        "steps": steps,
        "total": round(result["total"], 4),
        "target": TARGET_SECONDS,
        "passed": result["total"] < TARGET_SECONDS,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = f"spdx-export-web/{__version__}"

    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass

    # ------------------------------------------------------------- helpers
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data) -> None:
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self._json(status, {"error": message})

    # ------------------------------------------------------------- routes
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            page = resources.files("spdx_export").joinpath("webui", "index.html").read_bytes()
            self._send(200, page, "text/html; charset=utf-8")
        elif self.path == "/api/info":
            available = [{"name": n, "label": label} for n, label in SAMPLES.items()
                         if (SAMPLES_DIR / n).is_file()]
            self._json(200, {"version": __version__, "samples": available, "max_upload_mb": MAX_UPLOAD_BYTES // 2**20})
        else:
            self._error(404, "not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_UPLOAD_BYTES + 4096:
            self._error(413, f"file too large (limit {MAX_UPLOAD_BYTES // 2**20} MB)")
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._error(400, "request body must be JSON")
            return

        if self.path == "/api/convert":
            self._convert(payload)
        elif self.path == "/api/speed-test":
            self._json(200, speed_test())
        else:
            self._error(404, "not found")

    def _convert(self, payload: dict) -> None:
        sample = payload.get("sample")
        if sample is not None:
            if sample not in SAMPLES or not (SAMPLES_DIR / sample).is_file():
                self._error(400, "unknown sample")
                return
            self._json(200, analyze(SAMPLES_DIR / sample, sample))
            return

        name = str(payload.get("filename") or "")
        content = payload.get("content")
        suffix = Path(name).suffix.lower()
        if suffix not in (".json", ".csv"):
            self._error(400, "only .json and .csv files are supported")
            return
        if not isinstance(content, str):
            self._error(400, "missing file content")
            return
        if len(content.encode("utf-8")) > MAX_UPLOAD_BYTES:
            self._error(413, f"file too large (limit {MAX_UPLOAD_BYTES // 2**20} MB)")
            return
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"upload{suffix}"
            path.write_text(content, encoding="utf-8", newline="")
            self._json(200, analyze(path, Path(name).name))


def make_server(port: int = 8000, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="spdx-export-web", description="Web preview for the SPDX Export Tool")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)),
                    help="port to listen on (default: $PORT or 8000)")
    ap.add_argument("--host", default="127.0.0.1",
                    help="address to listen on; use 0.0.0.0 when deploying to a server")
    ap.add_argument("--no-browser", action="store_true", help="don't open the browser automatically")
    args = ap.parse_args(argv)

    try:
        server = make_server(args.port, args.host)
    except OSError:
        print(f"Port {args.port} is busy. Try: spdx-export-web --port 8010")
        return 3

    shown_host = "127.0.0.1" if args.host in ("0.0.0.0", "") else args.host
    url = f"http://{shown_host}:{server.server_address[1]}"
    print(f"SPDX Export Tool {__version__} - web preview")
    print(f"  Open {url} in your browser")
    print("  Press Ctrl+C to stop")
    if not args.no_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
