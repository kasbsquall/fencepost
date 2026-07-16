from __future__ import annotations

import json
import threading
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.request import urlopen

from fencepost.probe import probe_site_id, run_probes
from fencepost.report import build_report
from fencepost.serve import create_server
from fencepost.ui import load_report, render_artifact_page, render_report_document
from tests.fakes import FixtureComprehensionProbeAgent
from tests.test_probe import _records_with_two_gaps_at_one_site


class _DocumentFacts(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.tags: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        self.tags.append(tag)

    def handle_data(self, data) -> None:
        normalized = " ".join(data.split())
        if normalized:
            self.text.append(normalized)

    @property
    def visible_text(self) -> str:
        return " ".join(self.text)


def _fixture_report(tmp_path):
    triage, contexts, blame = _records_with_two_gaps_at_one_site()
    probe = run_probes(
        triage,
        contexts,
        blame=blame,
        agent=FixtureComprehensionProbeAgent(),
        answers={probe_site_id("pkg/analytics.py", 2): "I don't know"},
        artifact_dir=tmp_path,
    )
    build_report(
        commit="fixture-commit",
        student_email="student@example.edu",
        student_name="Diego Ramos",
        triage=triage,
        probe=probe,
        contexts=contexts,
        artifact_dir=tmp_path,
    )
    return tmp_path / "report" / "report.json"


def test_report_v2_renders_key_fixture_facts_without_a_browser(tmp_path) -> None:
    report_path = _fixture_report(tmp_path)
    report = load_report(report_path)
    document = render_report_document(report)
    parsed = _DocumentFacts()
    parsed.feed(document)
    visible = parsed.visible_text

    assert "Their suite passed; 1 site where understanding is unverified." in visible
    assert "STRICT equivalent rate" in visible
    assert "CONTRACT equivalent rate" in visible
    assert "0.000" in visible
    assert "0.500" in visible
    assert "CONTRACT limitation." in visible
    assert "Deliberately not asked" in visible
    assert "withheld from probes" in visible
    assert "10 passed" in visible
    assert "value >= 1" in visible
    assert "value > 1" in visible
    assert "assert False" in visible
    assert parsed.tags.count("details") >= 2
    assert "script" not in parsed.tags
    assert "https://" not in document

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["places"][0]["mutants"][0][
        "submitted_suite_tests_passed"
    ] == 10
    assert payload["places"][0]["mutants"][0][
        "submitted_suite_artifact_ref"
    ].startswith("mutants/")


def test_missing_and_old_reports_render_clear_full_page_errors(tmp_path) -> None:
    missing = render_artifact_page(tmp_path / "missing-artifact")
    missing_facts = _DocumentFacts()
    missing_facts.feed(missing)
    assert "No report.json was found" in missing_facts.visible_text
    assert "No partial report has been rendered." in missing_facts.visible_text

    old_root = tmp_path / "old" / "report"
    old_root.mkdir(parents=True)
    (old_root / "report.json").write_text(
        json.dumps({"schema_version": "1.0"}), encoding="utf-8"
    )
    old = render_artifact_page(old_root.parent)
    old_facts = _DocumentFacts()
    old_facts.feed(old)
    assert "requires report schema 2.0" in old_facts.visible_text
    assert "declares '1.0'" in old_facts.visible_text


def test_local_server_exposes_only_report_page_css_and_read_only_json(tmp_path) -> None:
    report_path = _fixture_report(tmp_path)
    expected_report = json.loads(report_path.read_text(encoding="utf-8"))
    server = create_server(tmp_path, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urlopen(base + "/", timeout=3) as response:
            assert response.status == 200
            assert "default-src 'none'" in response.headers[
                "Content-Security-Policy"
            ]
            assert "Their suite passed" in response.read().decode("utf-8")
        with urlopen(base + "/assets/ledger.css", timeout=3) as response:
            assert response.status == 200
            assert "#b24a3c" in response.read().decode("utf-8").casefold()
        with urlopen(base + "/report.json", timeout=3) as response:
            assert json.load(response) == expected_report
        try:
            urlopen(base + "/baseline/result.json", timeout=3)
        except HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("the report server exposed an arbitrary artifact path")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
