from __future__ import annotations

import json
import re
import threading
from contextlib import contextmanager
from html import escape
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fencepost.cli import _load_answers
from fencepost.probe import run_probes
from fencepost.probe_server import create_probe_server
from fencepost.ui import load_report
from fencepost.ui.student import _consequence_from_assertion
from tests.fakes import FixtureComprehensionProbeAgent
from tests.test_probe import _records_with_two_gaps_at_one_site
from tests.test_ui import _fixture_report


@contextmanager
def _running_probe(tmp_path: Path):
    artifact = tmp_path / "artifact"
    report_path = _fixture_report(artifact)
    output = tmp_path / "answers.json"
    server = create_probe_server(artifact, output, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield base, report_path, output
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def _get(url: str):
    with urlopen(url, timeout=3) as response:
        return response.read().decode("utf-8"), response.headers


def _post(url: str, fields: dict[str, str]):
    request = Request(
        url,
        data=urlencode(fields).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=3) as response:
        return response.read(), response.headers, response.geturl()


def _token(document: str) -> str:
    matched = re.search(r'name="csrf_token" value="([^"]+)"', document)
    assert matched is not None
    return matched.group(1)


def _first_evidence(report: dict) -> dict:
    return report["places"][0]["mutants"][0]


def test_consequence_is_derived_from_executed_equality_evidence() -> None:
    source = """def test_boundary():
    assert letter_grade(90) == "A"
"""
    failure = "AssertionError: assert 'B' == 'A'"

    assert _consequence_from_assertion(source, failure) == (
        "Calling <code>letter_grade(90)</code> returns "
        "<code>&#x27;B&#x27;</code> instead of <code>&#x27;A&#x27;</code>."
    )
    assert _consequence_from_assertion(source, "IndexError: out of range") is None


def test_preanswer_html_contains_no_mutant_or_execution_evidence(tmp_path) -> None:
    with _running_probe(tmp_path) as (base, report_path, output):
        report = load_report(report_path)
        place = report["places"][0]
        evidence_mutant = _first_evidence(report)
        mutation = evidence_mutant["mutation"]
        evidence = evidence_mutant["evidence"]

        start, headers = _get(base + "/")
        assert "form-action 'self'" in headers["Content-Security-Policy"]
        assert "script" not in start
        body, _, final_url = _post(
            base + "/begin", {"csrf_token": _token(start)}
        )
        question = body.decode("utf-8")
        assert final_url.endswith("/question/0")
        assert place["question"]["question_text"] in question
        assert escape(
            place["grounding"]["authored_lines"][0]["text"], quote=True
        ) in question

        secrets = (
            mutation["unified_diff"],
            mutation["mutated_segment"],
            evidence["adversarial_test"]["source"],
            evidence["adversarial_test"]["targeted_behavior"],
            evidence["failing_assertion"]["message"],
        )
        for secret in secrets:
            assert escape(secret, quote=True) not in question
        assert not output.exists()

        try:
            _get(base + "/reveal/0")
        except HTTPError as exc:
            assert exc.code == 403
            denied = exc.read().decode("utf-8")
            assert "Evidence is available only after an answer is recorded." in denied
            for secret in secrets:
                assert escape(secret, quote=True) not in denied
        else:
            raise AssertionError("unanswered evidence was reachable")

        try:
            _get(base + "/report.json")
        except HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("student server exposed report.json")


def test_blank_requires_explicit_unknown_and_round_trips_through_grading(tmp_path) -> None:
    with _running_probe(tmp_path) as (base, report_path, output):
        report = load_report(report_path)
        place = report["places"][0]
        site_id = place["site_id"]
        evidence_mutant = _first_evidence(report)
        mutation = evidence_mutant["mutation"]
        evidence = evidence_mutant["evidence"]

        start, _ = _get(base + "/")
        token = _token(start)
        question_bytes, _, _ = _post(base + "/begin", {"csrf_token": token})
        question = question_bytes.decode("utf-8")
        assert "I don" in question
        try:
            _post(
                base + "/answer/0",
                {
                    "csrf_token": token,
                    "site_id": site_id,
                    "answer": "",
                    "commitment": "answer",
                },
            )
        except HTTPError as exc:
            assert exc.code == 422
            retry = exc.read().decode("utf-8")
            assert "Write an answer" in retry
            assert escape(mutation["unified_diff"], quote=True) not in retry
            assert escape(evidence["failing_assertion"]["message"], quote=True) not in retry
        else:
            raise AssertionError("a blank answer reached the reveal")
        assert not output.exists()
        try:
            _get(base + "/reveal/0")
        except HTTPError as exc:
            assert exc.code == 403
        else:
            raise AssertionError("blank submission committed an answer")

        reveal_bytes, _, reveal_url = _post(
            base + "/answer/0",
            {
                "csrf_token": token,
                "site_id": site_id,
                "answer": "",
                "commitment": "unknown",
            },
        )
        reveal = reveal_bytes.decode("utf-8")
        assert reveal_url.endswith("/reveal/0")
        assert "I don&#x27;t know" in reveal
        assert escape(mutation["unified_diff"], quote=True) in reveal
        assert escape(evidence["failing_assertion"]["message"], quote=True) in reveal
        assert 'class="run run-ok"' in reveal
        assert 'class="run run-no"' in reveal
        assert 'class="execution-quote"' in reveal
        assert "state-icon" not in reveal
        assert not output.exists()

        _post(
            base + "/answer/0",
            {
                "csrf_token": token,
                "site_id": site_id,
                "answer": "This later edit must not replace the committed answer.",
                "commitment": "answer",
            },
        )
        between_bytes, _, between_url = _post(
            base + "/continue/0", {"csrf_token": token}
        )
        assert between_url.endswith("/between/0")
        assert "Answer recorded" in between_bytes.decode("utf-8")
        end, _ = _get(base + "/end")
        payload_bytes, headers, _ = _post(
            base + "/download", {"csrf_token": _token(end)}
        )
        assert "attachment" in headers["Content-Disposition"]
        assert json.loads(payload_bytes) == {site_id: "I don't know"}
        assert _load_answers(output) == {site_id: "I don't know"}

    triage, contexts, blame = _records_with_two_gaps_at_one_site()
    graded = run_probes(
        triage,
        contexts,
        blame=blame,
        agent=FixtureComprehensionProbeAgent(),
        answers=_load_answers(output),
        artifact_dir=tmp_path / "graded",
    )
    assert graded.submitted_answer_count == 1
    assert graded.graded_answer_count == 1
    assert graded.results[0].answer == "I don't know"
    assert graded.results[0].assessment is not None
    assert graded.results[0].assessment.verdict == "INSUFFICIENT"
