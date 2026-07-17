from __future__ import annotations

import json
import re
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest

from fencepost.probe_server import create_probe_server
from fencepost.serve import create_server
from fencepost.ui import load_report
from tests.test_ui import _fixture_report


def _assert_no_horizontal_overflow(page, *, view: str, width: int) -> None:
    dimensions = page.evaluate(
        """() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
        })"""
    )
    assert dimensions["scrollWidth"] <= dimensions["clientWidth"], (
        f"{view} overflows at {width}px: "
        f"{dimensions['scrollWidth']}px > {dimensions['clientWidth']}px"
    )


def _long_report(artifact_dir: Path) -> None:
    """Exercise the wells with paths, source, node ids, and assertions that cannot wrap."""
    report_path = _fixture_report(artifact_dir)
    report = load_report(report_path)
    unbroken = "unbroken_identifier_" * 24
    place = report["places"][0]
    grounding = place["grounding"]
    grounding["path"] = "nested/" * 24 + "analytics.py"
    authored = grounding["authored_lines"][0]
    authored["text"] = f"if {unbroken} >= 1:"
    mutation = place["mutants"][0]["mutation"]
    mutation["original_segment"] = ">="
    mutation["mutated_segment"] = ">"
    mutation["unified_diff"] = (
        f"- {authored['text']}\n+ {authored['text'].replace('>=', '>', 1)}"
    )
    failure = place["mutants"][0]["evidence"]["failing_assertion"]
    failure["nodeid"] = f"tests/test_{unbroken}.py::test_{unbroken}"
    failure["message"] = f"AssertionError: {unbroken}"
    report_path.write_text(json.dumps(report), encoding="utf-8")


@contextmanager
def _running_views(tmp_path: Path) -> Iterator[tuple[str, str]]:
    artifact = tmp_path / "artifact"
    _long_report(artifact)
    answers = tmp_path / "answers.json"
    probe = create_probe_server(artifact, answers, port=0)
    probe_thread = threading.Thread(target=probe.serve_forever, daemon=True)
    probe_thread.start()
    probe_base = f"http://127.0.0.1:{probe.server_address[1]}"
    report = create_server(artifact, port=0, probe_url=f"{probe_base}/")
    report_thread = threading.Thread(target=report.serve_forever, daemon=True)
    report_thread.start()
    report_base = f"http://127.0.0.1:{report.server_address[1]}"
    try:
        yield report_base, probe_base
    finally:
        report.shutdown()
        report.server_close()
        report_thread.join(timeout=3)
        probe.shutdown()
        probe.server_close()
        probe_thread.join(timeout=3)


def test_every_view_fits_without_horizontal_document_scroll(tmp_path) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    widths = (1440, 1280, 900)

    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for width in widths:
                with _running_views(tmp_path / str(width)) as (report_base, probe_base):
                    context = browser.new_context(viewport={"width": width, "height": 900})
                    page = context.new_page()
                    for path, name in (("/", "landing"), ("/report", "report"), ("/method", "method")):
                        page.goto(report_base + path, wait_until="networkidle")
                        _assert_no_horizontal_overflow(page, view=name, width=width)

                    page.goto(probe_base + "/", wait_until="networkidle")
                    _assert_no_horizontal_overflow(page, view="probe start", width=width)
                    page.get_by_role("button", name="Begin").click()
                    page.wait_for_url(re.compile(r".*/question/0$"))
                    _assert_no_horizontal_overflow(page, view="probe question", width=width)
                    page.locator("#answer").fill("I would check the boundary value.")
                    page.get_by_role("button", name="Submit answer").click()
                    page.wait_for_url(re.compile(r".*/reveal/0$"))
                    _assert_no_horizontal_overflow(page, view="probe reveal", width=width)
                    page.get_by_role("button", name="Continue").click()
                    page.wait_for_url(re.compile(r".*/between/0$"))
                    _assert_no_horizontal_overflow(page, view="probe between", width=width)
                    page.get_by_role("link", name="Next question").click()
                    page.wait_for_url(re.compile(r".*/end$"))
                    _assert_no_horizontal_overflow(page, view="probe end", width=width)
                    context.close()
        finally:
            browser.close()
