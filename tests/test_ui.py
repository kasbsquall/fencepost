from __future__ import annotations

import json
import threading
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.request import urlopen

from fencepost.probe import probe_site_id, run_probes
from fencepost.report import build_report
from fencepost.models import AuthoredLineCoverage
from fencepost.serve import create_server
from fencepost.ui import (
    load_report,
    render_artifact_page,
    render_method_document,
    render_report_document,
)
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
        submitted_suite_tests_passed=10,
        authored_line_coverage=AuthoredLineCoverage(
            authored_mutatable_line_count=1,
            covered_authored_mutatable_line_count=1,
            rate=1.0,
            minimum_rate=0.5,
            sufficient_for_assessment=True,
            artifact_ref="selection.json",
        ),
        mutant_results=tuple(item.mutant for item in triage.results),
        function_by_mutant_id={
            item.mutant.candidate.id: "f" for item in triage.results
        },
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

    assert "Diego Ramos's 10 tests pass." in visible
    assert "We made 3 small changes to code they wrote; their tests caught 0." in visible
    assert "Authored-line coverage" in visible
    assert "Their suite executes 1 of 1 mutatable lines they authored." in visible
    assert "What their tests already protect" in visible
    assert "Worth discussing" in visible
    assert "STRICT equivalent rate" not in visible
    assert "CONTRACT equivalent rate" not in visible
    assert "Deliberately not asked" in visible
    assert "withheld from probes" in visible
    assert "Their 10 tests — passed" in visible
    assert "value >= 1" in visible
    assert "value > 1" in visible
    assert "assert False" in visible
    assert "Full source diff" in visible
    assert "Execution evidence used for this assessment" in visible
    assert "suite-output" not in document
    assert parsed.tags.count("details") >= 2
    assert "script" not in parsed.tags
    assert "https://" not in document

    method = render_method_document(report)
    method_facts = _DocumentFacts()
    method_facts.feed(method)
    assert "STRICT equivalent rate" in method_facts.visible_text
    assert "CONTRACT equivalent rate" in method_facts.visible_text
    assert "0.000" in method_facts.visible_text
    assert "0.500" in method_facts.visible_text
    assert "CONTRACT limitation." in method_facts.visible_text

    report_withheld = json.loads(json.dumps(report))
    report_withheld["pedagogically_not_asked"] = [
        {
            "mutant": report_withheld["places"][0]["mutants"][0],
            "reason_codes": ["implicit_bool_as_number"],
            "reasons": ["Fixture witness treats a boolean as a number."],
        }
    ]
    withheld_document = render_report_document(report_withheld)
    withheld_facts = _DocumentFacts()
    withheld_facts.feed(withheld_document)
    assert "treating a boolean as a number" in withheld_facts.visible_text
    assert "Technical evidence for audit" in withheld_facts.visible_text

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["places"][0]["mutants"][0][
        "submitted_suite_tests_passed"
    ] == 10
    assert payload["places"][0]["mutants"][0][
        "submitted_suite_artifact_ref"
    ].startswith("mutants/")
    assert payload["submitted_suite_tests_passed"] == 10
    assert payload["places"][0]["mutants"][0]["mutation"]["unified_diff"]
    assert payload["places"][0]["assessment"]["citations"]


def test_low_authored_line_coverage_is_not_rendered_as_a_clean_report(tmp_path) -> None:
    report = load_report(_fixture_report(tmp_path))
    report["student_name"] = "Lazy Student"
    report["submitted_suite_tests_passed"] = 1
    report["authored_line_coverage"] = {
        "authored_mutatable_line_count": 4,
        "covered_authored_mutatable_line_count": 1,
        "rate": 0.25,
        "minimum_rate": 0.5,
        "sufficient_for_assessment": False,
        "artifact_ref": "selection.json",
    }
    report["mutation_summary"] = {
        "total_mutants": 0,
        "killed_by_submitted_tests": 0,
        "survived_submitted_tests": 0,
        "broken_mutants": 0,
    }
    report["function_assessments"] = []
    report["function_groups"] = []
    report["places"] = []
    report["question_mutant_count"] = 0
    report["unverified_place_count"] = 0
    report["question_count"] = 0
    document = render_report_document(report)
    parsed = _DocumentFacts()
    parsed.feed(document)
    assert "Lazy Student's 1 tests pass, but they execute 1 of 4" in parsed.visible_text
    assert "Fencepost cannot assess understanding of code their tests never run." in parsed.visible_text
    assert "Coverage: 25%" in parsed.visible_text
    assert "Question generation is inconclusive" in parsed.visible_text
    assert "No fair question sites are present" not in parsed.visible_text
    assert "0 sites where understanding is unverified" not in parsed.visible_text


def test_absent_test_count_never_falls_back_to_pytest_stdout(tmp_path) -> None:
    report = load_report(_fixture_report(tmp_path))
    report["places"][0]["mutants"][0]["submitted_suite_tests_passed"] = None
    report["places"][0]["mutants"][0]["mutant"]["execution"][
        "stdout"
    ] = "999 passed -- this must not become UI copy"
    document = render_report_document(report)
    parsed = _DocumentFacts()
    parsed.feed(document)
    assert "Their submitted tests — passed" in parsed.visible_text
    assert "999 passed" not in parsed.visible_text
    assert "suite-output" not in document


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
            page = response.read().decode("utf-8")
            assert "Diego Ramos" in page
            assert "10 tests pass." in page
        with urlopen(base + "/method", timeout=3) as response:
            assert response.status == 200
            method = response.read().decode("utf-8")
            assert "STRICT equivalent rate" in method
            assert "CONTRACT equivalent rate" in method
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
