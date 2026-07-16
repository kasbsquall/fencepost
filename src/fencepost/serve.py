"""Tiny read-only HTTP server for the local Fencepost instructor view."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

from .ui import (
    ReportUiError,
    load_report,
    render_error_document,
    render_method_document,
    render_report_document,
)
from .ui import resolve_report_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fencepost serve",
        description="Open a read-only local instructor view for a Fencepost report v2 artifact.",
    )
    parser.add_argument("artifact_dir", type=Path, help="Fencepost run artifact directory")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the system browser automatically",
    )
    return parser


def _security_headers(handler: BaseHTTPRequestHandler) -> None:
    handler.send_header(
        "Content-Security-Policy",
        "default-src 'none'; style-src 'self'; img-src 'self' data:; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    )
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("Cache-Control", "no-store")


def _handler(
    *, page: bytes, method_page: bytes, stylesheet: bytes, report_json: bytes | None
) -> type[BaseHTTPRequestHandler]:
    class ReportHandler(BaseHTTPRequestHandler):
        server_version = "FencepostReport/2.0"

        def _respond(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            _security_headers(self)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            path = urlsplit(self.path).path
            if path in {"/", "/index.html"}:
                self._respond(200, "text/html; charset=utf-8", page)
            elif path in {"/method", "/method/"}:
                self._respond(200, "text/html; charset=utf-8", method_page)
            elif path == "/assets/ledger.css":
                self._respond(200, "text/css; charset=utf-8", stylesheet)
            elif path == "/report.json" and report_json is not None:
                self._respond(200, "application/json; charset=utf-8", report_json)
            else:
                self._respond(404, "text/plain; charset=utf-8", b"Not found\n")

        def do_HEAD(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            self.do_GET()

        def log_message(self, format: str, *args: object) -> None:
            print(f"fencepost serve: {format % args}", file=sys.stderr)

    return ReportHandler


def create_server(
    artifact_dir: Path, *, host: str = "127.0.0.1", port: int = 8765
) -> ThreadingHTTPServer:
    """Create a server that exposes only the rendered page, CSS, and report JSON."""
    report_json = None
    try:
        report_path = resolve_report_path(artifact_dir)
        report = load_report(report_path)
    except ReportUiError as exc:
        page_text = render_error_document(str(exc))
        method_text = page_text
    else:
        page_text = render_report_document(report)
        method_text = render_method_document(report)
        report_json = (
            json.dumps(report, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
    stylesheet = files("fencepost.ui").joinpath("ledger.css").read_bytes()
    handler = _handler(
        page=page_text.encode("utf-8"),
        method_page=method_text.encode("utf-8"),
        stylesheet=stylesheet,
        report_json=report_json,
    )
    return ThreadingHTTPServer((host, port), handler)


def serve_artifact(
    artifact_dir: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> int:
    """Serve until interrupted; no artifact path is ever opened for writing."""
    try:
        server = create_server(artifact_dir, host=host, port=port)
    except OSError as exc:
        print(f"fencepost serve: cannot bind {host}:{port}: {exc}", file=sys.stderr)
        return 2
    actual_host, actual_port = server.server_address[:2]
    browser_host = "127.0.0.1" if actual_host in {"0.0.0.0", "::"} else actual_host
    url = f"http://{browser_host}:{actual_port}/"
    print(f"Fencepost report: {url}")
    print("Read-only local view. Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nFencepost report server stopped.")
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return serve_artifact(
        args.artifact_dir,
        host=args.host,
        port=args.port,
        open_browser=not args.no_open,
    )


if __name__ == "__main__":
    raise SystemExit(main())
