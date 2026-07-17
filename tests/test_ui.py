from __future__ import annotations

import json
import re
import threading
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fencepost.probe import probe_site_id, run_probes
from fencepost.report import build_report
from fencepost.models import AuthoredLineCoverage
from fencepost.serve import create_server
from fencepost.ui import (
    load_report,
    render_artifact_page,
    render_landing_document,
    render_method_document,
    render_report_document,
)
from fencepost.ui.student import (
    render_probe_between,
    render_probe_end,
    render_probe_error,
    render_probe_question,
    render_probe_reveal,
    render_probe_start,
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
        self.text.append(" ")

    def handle_endtag(self, tag) -> None:
        self.text.append(" ")

    def handle_data(self, data) -> None:
        self.text.append(data)

    @property
    def visible_text(self) -> str:
        return " ".join("".join(self.text).split())


def _assert_no_mojibake(*documents: str) -> None:
    """Guard what users see, not the source encoding that produced it."""
    signatures = (
        chr(0x00E2) + chr(0x20AC),  # broken UTF-8 punctuation prefix
        chr(0x00C2),                 # a stray Â prefix
        chr(0x00EF) + chr(0x00BB) + chr(0x00BF),  # a visible UTF-8 BOM
    )
    for document in documents:
        for signature in signatures:
            assert signature not in document


def _assert_headline_facts(report, visible: str) -> None:
    """Check execution facts without coupling the test to inline presentational spans."""
    tests = report["submitted_suite_tests_passed"]
    mutation = report["mutation_summary"]
    total = mutation["total_mutants"]
    killed = mutation["killed_by_submitted_tests"]
    missed = mutation["survived_submitted_tests"]
    fair = report["question_mutant_count"]
    withheld = report["not_questioned_mutant_count"]

    assert re.search(rf"\b{tests}\s+tests\b", visible)
    assert re.search(r"\btests?\s+pass(?:es)?\b", visible, re.IGNORECASE)
    assert re.search(rf"\b{total}\s+small\s+changes\b", visible)
    assert re.search(rf"\btests\s+caught\s+{killed}\b", visible)
    assert re.search(rf"\b{missed}\s+changes\s+they\s+missed\b", visible)
    assert re.search(rf"\b{fair}\s+are\s+fair\s+to\s+discuss\b", visible)
    assert re.search(rf"\bwithheld\s+{withheld}\s+change", visible)


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


def test_every_rendered_view_is_free_of_utf8_mojibake(tmp_path) -> None:
    report = load_report(_fixture_report(tmp_path))
    place = report["places"][0]
    documents = (
        render_landing_document(
            report,
            artifact_dir=tmp_path,
            probe_url="http://127.0.0.1:8766/",
        ),
        render_report_document(report),
        render_method_document(report),
        render_probe_start(report, total=1, token="test-token"),
        render_probe_question(place, index=0, total=1, token="test-token"),
        render_probe_reveal(
            place,
            answer="I don't know",
            index=0,
            total=1,
            token="test-token",
            previous_index=None,
        ),
        render_probe_between(index=0, total=1, next_url="/end"),
        render_probe_end(total=1, token="test-token"),
        render_probe_error("That question does not exist."),
    )
    _assert_no_mojibake(*documents)


def test_landing_commands_are_portable_and_do_not_expose_absolute_paths(tmp_path) -> None:
    report = load_report(_fixture_report(tmp_path))
    report["repository_path"] = str(Path.cwd() / "demo" / "student-repo")
    report["student_email"] = "d.ramos@alumnos.ejemplo.edu"
    document = render_landing_document(
        report,
        artifact_dir=tmp_path / ".fp_demo",
        probe_url="http://127.0.0.1:8766/",
    )

    assert (
        "fencepost demo/student-repo --student-email "
        "d.ramos@alumnos.ejemplo.edu --output .fp_run"
    ) in document
    assert "fencepost serve .fp_run" in document
    assert "fencepost probe .fp_run --out answers.json" in document
    assert str(Path.cwd()) not in document


def test_report_v2_renders_key_fixture_facts_without_a_browser(tmp_path) -> None:
    report_path = _fixture_report(tmp_path)
    report = load_report(report_path)
    authored_line = report["places"][0]["grounding"]["authored_lines"][0]
    authored_line.update(
        {
            "committer_name": "Course Bot",
            "committer_email": "bot@example.edu",
            "author_matches_committer": False,
            "co_authors": [{"name": "Sam Partner", "email": "sam@example.edu"}],
            "history_rewrite_signals": ["author_committer_identity_mismatch"],
            "moved_by_blame": True,
            "copied_by_blame": False,
            "origin_path": "pkg/analytics.py",
            "origin_line": 2,
        }
    )
    report["attribution_summary"] = {
        "method": "git blame -M -C -C -w --line-porcelain",
        "limitation": (
            "Git blame attributes lines to the commit history it can trace, not to "
            "the person who was at the keyboard."
        ),
        "coauthored_excluded_line_count": 1,
        "author_committer_mismatch_commit_count": 1,
        "moved_line_count": 1,
        "copied_line_count": 0,
        "repository_history_signals": ["shallow_repository"],
        "commits": [
            {
                "commit": "fixture-commit",
                "author_email": "student@example.edu",
                "committer_email": "bot@example.edu",
                "co_authors": [
                    {"name": "Sam Partner", "email": "sam@example.edu"}
                ],
                "history_rewrite_signals": [
                    "author_committer_identity_mismatch"
                ],
            }
        ],
    }
    report["run_started_at"] = "2026-07-16T19:34:54.565028+00:00"
    group = report["function_groups"][0]
    summary = authored_line["commit_summary"]
    group["ranking_signals"] = ["commit_claim"]
    group["priority_reason"] = (
        f'Commit {authored_line["commit"][:7]} says "{summary}", '
        "but execution shows the submitted tests did not protect that claimed behavior."
    )
    document = render_report_document(report)
    parsed = _DocumentFacts()
    parsed.feed(document)
    visible = parsed.visible_text

    _assert_headline_facts(report, visible)
    assert "Authored-line coverage" in visible
    assert "Their suite executes 1 of 1 mutatable lines Git attributes to them." in visible
    assert "What their tests already protect" in visible
    assert "Worth discussing" in visible
    assert "STRICT equivalent rate" not in visible
    assert "CONTRACT equivalent rate" not in visible
    assert "Deliberately not asked" in visible
    assert "withheld from probes" in visible
    assert "Their submitted suite" in visible
    assert re.search(r"\bpassed\s+10\s+tests\b", visible)
    assert "value >= 1" in visible
    assert "value > 1" in visible
    assert "value ≥ 1" not in visible
    assert "assert False" in visible
    assert "Full source diff" in visible
    assert "Execution evidence used for this assessment" in visible
    assert "What Git can and cannot tell us" in visible
    assert "person who was at the keyboard" in visible
    assert "1 student-attributed line excluded because the commit carries a co-author trailer." in visible
    assert "1 analyzed commit where author and committer differ." in visible
    assert "Inspect analyzed commit signals" in visible
    assert "co-author trailer: sam@example.edu" in visible
    assert "-M move match" in visible
    assert "blame origin pkg/analytics.py:2" in visible
    hero = document.split('<article class="question-card"', 1)[1].split(
        "</article>", 1
    )[0]
    assert "Top-ranked execution evidence" in hero
    assert "value &gt;= 1" in hero
    assert "value &gt; 1" in hero
    assert hero.count(summary) == 1
    assert hero.count(authored_line["commit"][:7]) == 1
    assert "Their commit says" in hero
    assert "Their submitted suite" in hero
    assert "assert False" in hero
    assert "<details" not in hero
    assert 'class="run run-ok"' in hero
    assert 'class="run run-no"' in hero
    assert 'class="execution-quote"' in hero
    assert "state-icon" not in hero
    assert 'class="brand-post-offset"' in document
    assert document.index('<article class="question-card"') < document.index(
        '<section class="function-outcomes"'
    )
    headline_markup = document.split('<h1 id="run-title">', 1)[1].split("</h1>", 1)[0]
    assert "Diego Ramos" not in headline_markup
    assert "suite-output" not in document
    assert parsed.tags.count("details") >= 2
    assert "script" not in parsed.tags
    assert "https://" not in document
    assert '<time datetime="2026-07-16T19:34:54.565028+00:00">Jul 16, 2026</time>' in document

    chart_report = json.loads(json.dumps(report))
    chart_report["mutation_summary"] = {
        "total_mutants": 51,
        "killed_by_submitted_tests": 30,
        "survived_submitted_tests": 21,
        "broken_mutants": 0,
    }
    chart_report["question_mutant_count"] = 20
    chart_report["not_questioned_mutant_count"] = 1
    chart_report["function_assessments"] = [
        {
            "path": "pkg/analytics.py",
            "qualified_function_name": "letter_grade",
            "status": "GAPS_FOUND",
            "total_mutants": 20,
            "killed_by_submitted_tests": 8,
            "survived_submitted_tests": 12,
            "broken_mutants": 0,
            "contract_real_gap_mutants": 12,
            "question_mutants": 12,
            "not_questioned_mutants": 0,
            "question_site_count": 4,
            "artifact_refs": [],
        },
        {
            "path": "pkg/analytics.py",
            "qualified_function_name": "rank",
            "status": "CLEAN",
            "total_mutants": 10,
            "killed_by_submitted_tests": 10,
            "survived_submitted_tests": 0,
            "broken_mutants": 0,
            "contract_real_gap_mutants": 0,
            "question_mutants": 0,
            "not_questioned_mutants": 0,
            "question_site_count": 0,
            "artifact_refs": [],
        },
        {
            "path": "pkg/analytics.py",
            "qualified_function_name": "top_n",
            "status": "CLEAN",
            "total_mutants": 4,
            "killed_by_submitted_tests": 4,
            "survived_submitted_tests": 0,
            "broken_mutants": 0,
            "contract_real_gap_mutants": 0,
            "question_mutants": 0,
            "not_questioned_mutants": 0,
            "question_site_count": 0,
            "artifact_refs": [],
        },
    ]
    chart_document = render_report_document(chart_report)
    chart_facts = _DocumentFacts()
    chart_facts.feed(chart_document)
    assert re.search(r"\b30\s+caught\b", chart_facts.visible_text)
    assert re.search(r"\b20\s+worth\s+discussing\b", chart_facts.visible_text)
    assert re.search(r"\b1\s+withheld\b", chart_facts.visible_text)
    overview = chart_document.split('<div class="headline-flow"', 1)[1].split(
        "</div>", 1
    )[0]
    assert overview.index("flow-caught") < overview.index("flow-discuss")
    assert overview.index("flow-discuss") < overview.index("flow-withheld")
    assert 'colspan="30"' in overview
    assert 'colspan="20"' in overview
    assert 'colspan="1"' in overview
    function_flows = chart_document.split(
        '<div class="function-flow-list"', 1
    )[1]
    assert function_flows.index("rank") < function_flows.index("letter_grade")
    assert function_flows.index("top_n") < function_flows.index("letter_grade")

    missing_segment = json.loads(json.dumps(chart_report))
    del missing_segment["not_questioned_mutant_count"]
    missing_document = render_report_document(missing_segment)
    missing_overview = missing_document.split(
        '<div class="headline-flow"', 1
    )[1].split("</div>", 1)[0]
    assert "flow-withheld" not in missing_overview

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
    assert "Lazy Student" in parsed.visible_text
    assert "One test passes. Coverage is too low to assess." in parsed.visible_text
    assert "Their suite executes 1 of 4" in parsed.visible_text
    assert "mutatable lines Git attributes to this student." in parsed.visible_text
    assert "Fencepost cannot assess code their tests never run." in parsed.visible_text
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
    assert re.search(r"\bTheir submitted suite\s+passed\b", parsed.visible_text)
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


def test_local_server_exposes_only_known_read_only_routes(tmp_path) -> None:
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
            page_facts = _DocumentFacts()
            page_facts.feed(page)
            assert "Choose where you enter the conversation." in page_facts.visible_text
            assert "Instructor view" in page_facts.visible_text
            assert "Student view" in page_facts.visible_text
            assert 'href="/report"' in page
            assert 'href="/method"' in page
            assert 'href="http://127.0.0.1:8766/"' in page
        with urlopen(base + "/report", timeout=3) as response:
            assert response.status == 200
            report_page = response.read().decode("utf-8")
            report_facts = _DocumentFacts()
            report_facts.feed(report_page)
            _assert_headline_facts(expected_report, report_facts.visible_text)
        with urlopen(base + "/method", timeout=3) as response:
            assert response.status == 200
            method = response.read().decode("utf-8")
            assert "STRICT equivalent rate" in method
            assert "CONTRACT equivalent rate" in method
        with urlopen(base + "/assets/direction-d.css", timeout=3) as response:
            assert response.status == 200
            stylesheet = response.read().decode("utf-8").casefold()
            assert "#0b0c0e" in stylesheet
            assert "#3dd68c" in stylesheet
            assert "border-spacing: 3px 0" in stylesheet
            assert 'font-feature-settings: "liga" 0, "calt" 0' in stylesheet
            assert "font-variant-ligatures: none" in stylesheet
        with urlopen(base + "/report.json", timeout=3) as response:
            assert json.load(response) == expected_report
        for unknown_path in (
            "/baseline/result.json",
            "/run.json",
            "/summary.json",
            "/probe/summary.json",
            "/answers.json",
            "/assets/ledger.css",
        ):
            try:
                urlopen(base + unknown_path, timeout=3)
            except HTTPError as exc:
                assert exc.code == 404
            else:
                raise AssertionError(
                    f"the report server exposed arbitrary artifact path {unknown_path}"
                )
        try:
            urlopen(Request(base + "/report.json", data=b"{}", method="POST"), timeout=3)
        except HTTPError as exc:
            assert exc.code == 501
        else:
            raise AssertionError("the read-only report server accepted a write")
        assert json.loads(report_path.read_text(encoding="utf-8")) == expected_report
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
