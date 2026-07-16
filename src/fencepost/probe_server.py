"""Local server-rendered student probe flow.

Evidence is selected into a response only after the corresponding answer is
committed in server memory.  The artifact itself is never exposed or written.
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
import threading
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit

from .ui import ReportUiError, load_report, resolve_report_path
from .ui.student import (
    render_probe_between,
    render_probe_end,
    render_probe_error,
    render_probe_question,
    render_probe_reveal,
    render_probe_start,
)


MAX_FORM_BYTES = 1_000_000
UNKNOWN_ANSWER = "I don't know"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fencepost probe",
        description=(
            "Walk a student through report questions before revealing execution evidence."
        ),
    )
    parser.add_argument("artifact_dir", type=Path, help="Fencepost run artifact directory")
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Write this answers JSON file only when the student downloads it",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8766, help="Bind port (default: 8766)")
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the system browser automatically",
    )
    return parser


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _ordered_places(report: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    by_id = {
        item.get("site_id"): item
        for item in (_mapping(value) for value in _sequence(report.get("places")))
        if isinstance(item.get("site_id"), str)
        and isinstance(_mapping(item.get("question")).get("question_text"), str)
    }
    ordered: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for group in (_mapping(value) for value in _sequence(report.get("function_groups"))):
        for site_id in _sequence(group.get("site_ids")):
            if site_id in by_id and site_id not in seen:
                ordered.append(by_id[site_id])
                seen.add(site_id)
    for site_id, place in by_id.items():
        if site_id not in seen:
            ordered.append(place)
    return tuple(ordered)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


@dataclass
class ProbeSession:
    report: Mapping[str, Any]
    places: tuple[Mapping[str, Any], ...]
    answers_path: Path
    token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    answers: dict[str, str] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)

    def first_unanswered(self) -> int | None:
        for index, place in enumerate(self.places):
            if place["site_id"] not in self.answers:
                return index
        return None

    def answered(self, index: int) -> bool:
        return self.places[index]["site_id"] in self.answers


def _security_headers(handler: BaseHTTPRequestHandler) -> None:
    handler.send_header(
        "Content-Security-Policy",
        "default-src 'none'; style-src 'self'; img-src 'self' data:; "
        "base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
    )
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("Cache-Control", "no-store")


def _handler(
    *, session: ProbeSession, stylesheet: bytes
) -> type[BaseHTTPRequestHandler]:
    class StudentProbeHandler(BaseHTTPRequestHandler):
        server_version = "FencepostProbe/2.0"

        def _respond(
            self,
            status: int,
            content_type: str,
            body: bytes,
            *,
            disposition: str | None = None,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            if disposition:
                self.send_header("Content-Disposition", disposition)
            _security_headers(self)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _html(self, document: str, status: int = 200) -> None:
            self._respond(status, "text/html; charset=utf-8", document.encode("utf-8"))

        def _redirect(self, location: str) -> None:
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            _security_headers(self)
            self.end_headers()

        def _form(self) -> dict[str, list[str]] | None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return None
            if length < 0 or length > MAX_FORM_BYTES:
                return None
            try:
                body = self.rfile.read(length).decode("utf-8")
            except UnicodeDecodeError:
                return None
            return parse_qs(body, keep_blank_values=True, strict_parsing=False)

        def _valid_token(self, form: Mapping[str, list[str]]) -> bool:
            supplied = form.get("csrf_token", [""])[0]
            return secrets.compare_digest(supplied, session.token)

        def _bad_request(self) -> None:
            self._html(render_probe_error("The submitted form was not valid."), 400)

        def _index(self, pattern: str, path: str) -> int | None:
            matched = re.fullmatch(pattern, path)
            return int(matched.group(1)) if matched else None

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            path = urlsplit(self.path).path
            total = len(session.places)
            if path in {"/", "/index.html"}:
                self._html(
                    render_probe_start(
                        session.report, total=total, token=session.token
                    )
                )
                return
            if path == "/assets/ledger.css":
                self._respond(200, "text/css; charset=utf-8", stylesheet)
                return
            if path == "/end":
                with session.lock:
                    current = session.first_unanswered()
                if current is not None:
                    self._redirect(f"/question/{current}")
                else:
                    self._html(render_probe_end(total=total, token=session.token))
                return

            question_index = self._index(r"/question/([0-9]+)", path)
            if question_index is not None:
                if not 0 <= question_index < total:
                    self._html(render_probe_error("That question does not exist."), 404)
                    return
                with session.lock:
                    if session.answered(question_index):
                        self._redirect(f"/reveal/{question_index}")
                        return
                    current = session.first_unanswered()
                if current != question_index:
                    self._redirect("/end" if current is None else f"/question/{current}")
                    return
                self._html(
                    render_probe_question(
                        session.places[question_index],
                        index=question_index,
                        total=total,
                        token=session.token,
                    )
                )
                return

            reveal_index = self._index(r"/reveal/([0-9]+)", path)
            if reveal_index is not None:
                if not 0 <= reveal_index < total:
                    self._html(render_probe_error("That reveal does not exist."), 404)
                    return
                with session.lock:
                    if not session.answered(reveal_index):
                        self._html(
                            render_probe_error(
                                "Evidence is available only after an answer is recorded."
                            ),
                            403,
                        )
                        return
                    site_id = session.places[reveal_index]["site_id"]
                    answer = session.answers[site_id]
                    previous = next(
                        (
                            index
                            for index in range(reveal_index - 1, -1, -1)
                            if session.answered(index)
                        ),
                        None,
                    )
                self._html(
                    render_probe_reveal(
                        session.places[reveal_index],
                        answer=answer,
                        index=reveal_index,
                        total=total,
                        token=session.token,
                        previous_index=previous,
                    )
                )
                return

            between_index = self._index(r"/between/([0-9]+)", path)
            if between_index is not None:
                if not 0 <= between_index < total:
                    self._html(render_probe_error("That question does not exist."), 404)
                    return
                with session.lock:
                    answered = session.answered(between_index)
                if not answered:
                    self._redirect(f"/question/{between_index}")
                    return
                next_url = (
                    f"/question/{between_index + 1}"
                    if between_index + 1 < total
                    else "/end"
                )
                self._html(
                    render_probe_between(
                        index=between_index,
                        total=total,
                        next_url=next_url,
                    )
                )
                return

            self._respond(404, "text/plain; charset=utf-8", b"Not found\n")

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            path = urlsplit(self.path).path
            form = self._form()
            if form is None or not self._valid_token(form):
                self._bad_request()
                return
            total = len(session.places)
            if path == "/begin":
                with session.lock:
                    current = session.first_unanswered()
                self._redirect("/end" if current is None else f"/question/{current}")
                return

            answer_index = self._index(r"/answer/([0-9]+)", path)
            if answer_index is not None:
                if not 0 <= answer_index < total:
                    self._bad_request()
                    return
                with session.lock:
                    place = session.places[answer_index]
                    site_id = place["site_id"]
                    if form.get("site_id", [""])[0] != site_id:
                        self._bad_request()
                        return
                    if not session.answered(answer_index):
                        current = session.first_unanswered()
                        if current != answer_index:
                            self._redirect(
                                "/end" if current is None else f"/question/{current}"
                            )
                            return
                        commitment = form.get("commitment", [""])[0]
                        typed_answer = form.get("answer", [""])[0]
                        if commitment == "unknown":
                            answer = UNKNOWN_ANSWER
                        elif commitment == "answer" and typed_answer.strip():
                            answer = typed_answer
                        elif commitment == "answer":
                            self._html(
                                render_probe_question(
                                    place,
                                    index=answer_index,
                                    total=total,
                                    token=session.token,
                                    validation_message=(
                                        "Write an answer, or choose â€œI donâ€™t knowâ€ "
                                        "to continue."
                                    ),
                                ),
                                422,
                            )
                            return
                        else:
                            self._bad_request()
                            return
                        session.answers[site_id] = answer
                self._redirect(f"/reveal/{answer_index}")
                return

            continue_index = self._index(r"/continue/([0-9]+)", path)
            if continue_index is not None:
                if not 0 <= continue_index < total:
                    self._bad_request()
                    return
                with session.lock:
                    answered = session.answered(continue_index)
                self._redirect(
                    f"/between/{continue_index}"
                    if answered
                    else f"/question/{continue_index}"
                )
                return

            if path == "/download":
                with session.lock:
                    current = session.first_unanswered()
                    answers = dict(session.answers)
                if current is not None:
                    self._redirect(f"/question/{current}")
                    return
                payload = (json.dumps(answers, indent=2, sort_keys=True) + "\n").encode(
                    "utf-8"
                )
                try:
                    session.answers_path.write_bytes(payload)
                except OSError as exc:
                    self._html(
                        render_probe_error(f"answers.json could not be written: {exc}"),
                        500,
                    )
                    return
                safe_name = session.answers_path.name.replace('"', "")
                self._respond(
                    200,
                    "application/json; charset=utf-8",
                    payload,
                    disposition=f'attachment; filename="{safe_name}"',
                )
                return

            self._respond(404, "text/plain; charset=utf-8", b"Not found\n")

        def log_message(self, format: str, *args: object) -> None:
            print(f"fencepost probe: {format % args}", file=sys.stderr)

    return StudentProbeHandler


def create_probe_server(
    artifact_dir: Path,
    answers_path: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
) -> ThreadingHTTPServer:
    """Create a dynamic student server without exposing the report artifact."""
    report_path = resolve_report_path(artifact_dir)
    report = load_report(report_path)
    artifact_root = artifact_dir.expanduser().resolve()
    output = answers_path.expanduser().resolve()
    if _is_within(output, artifact_root):
        raise ReportUiError("--out must be outside the read-only artifact directory")
    if not output.parent.is_dir():
        raise ReportUiError(f"answers output directory does not exist: {output.parent}")
    session = ProbeSession(
        report=report,
        places=_ordered_places(report),
        answers_path=output,
    )
    stylesheet = files("fencepost.ui").joinpath("ledger.css").read_bytes()
    handler = _handler(session=session, stylesheet=stylesheet)
    server = ThreadingHTTPServer((host, port), handler)
    server.probe_session = session  # type: ignore[attr-defined]
    return server


def serve_probe(
    artifact_dir: Path,
    answers_path: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
    open_browser: bool = True,
) -> int:
    try:
        server = create_probe_server(
            artifact_dir, answers_path, host=host, port=port
        )
    except (OSError, ReportUiError) as exc:
        print(f"fencepost probe: {exc}", file=sys.stderr)
        return 2
    actual_host, actual_port = server.server_address[:2]
    browser_host = "127.0.0.1" if actual_host in {"0.0.0.0", "::"} else actual_host
    url = f"http://{browser_host}:{actual_port}/"
    print(f"Fencepost student probe: {url}")
    print(f"Answers will be written only on download: {answers_path.resolve()}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nFencepost student probe stopped.")
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return serve_probe(
        args.artifact_dir,
        args.out,
        host=args.host,
        port=args.port,
        open_browser=not args.no_open,
    )


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["ProbeSession", "create_probe_server", "serve_probe"]
