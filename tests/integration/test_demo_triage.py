"""Hermetic Stage 5 gate: model seam is fake, every label is Docker-decided."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fencepost import RunConfig, TriageConfig, run_analysis
from fencepost.probe import probe_site_id
from tests.fakes import (
    FixtureAdversarialTestGenerator,
    FixtureComprehensionProbeAgent,
)


ROOT = Path(__file__).resolve().parents[2]


def test_demo_survivors_are_triaged_with_execution_evidence(tmp_path: Path) -> None:
    repo = tmp_path / "student-repo"
    subprocess.run(
        [sys.executable, str(ROOT / "demo" / "build_demo_repo.py"), str(repo)],
        check=True,
        cwd=ROOT,
    )
    generator = FixtureAdversarialTestGenerator()
    probe_agent = FixtureComprehensionProbeAgent()
    result = run_analysis(
        RunConfig(
            repo=repo,
            student_email="d.ramos@alumnos.ejemplo.edu",
            artifact_dir=tmp_path / "artifact",
        ),
        adversarial_generator=generator,
        triage_config=TriageConfig(valid_attempts=3, invalid_retry_limit=3),
        probe_agent=probe_agent,
        probe_answers={
            probe_site_id("gradebook/analytics.py", 13): (
                "At exactly 90 the strict comparison skips A and returns B because "
                "equality no longer satisfies the boundary."
            )
        },
    )

    assert result.triage is not None
    triage = result.triage
    stage4_survivors = {
        mutant.candidate.id
        for mutant in result.mutant_results
        if mutant.execution.status == "survived"
    }
    stage4_killed = {
        mutant.candidate.id
        for mutant in result.mutant_results
        if mutant.execution.status == "killed"
    }
    triaged_ids = {item.mutant.candidate.id for item in triage.results}

    assert len(stage4_survivors) == 21
    assert len(stage4_killed) == 30
    assert triage.total_survivors == 21
    assert triaged_ids == stage4_survivors
    assert triaged_ids.isdisjoint(stage4_killed)
    assert triage.real_gap_count_strict == 21
    assert triage.probable_equivalent_count_strict == 0
    assert triage.unresolved_count_strict == 0
    assert triage.equivalent_rate_strict == 0.0
    assert triage.real_gap_count_contract == 20
    assert triage.probable_equivalent_count_contract == 1
    assert triage.unresolved_count_contract == 0
    assert triage.equivalent_rate_contract == 1 / 21
    assert triage.invalid_contract_attempts == 1
    assert triage.triage_complete is True
    assert {item.label_strict for item in triage.results} == {"REAL_GAP"}
    assert {item.label_contract for item in triage.results} == {
        "REAL_GAP",
        "PROBABLE_EQUIVALENT",
    }
    for item in triage.results:
        assert item.strict.winning_test is not None
        assert item.strict.failure_evidence is not None
        winning = item.strict.attempts[-1]
        assert winning.original.status == "passed"
        assert winning.mutant is not None
        assert winning.mutant.status in {"failed", "timed_out"}
        if item.label_contract == "REAL_GAP":
            assert item.contract.winning_test is not None
            assert item.contract.failure_evidence is not None

    required_segments = {
        "score >= 90",
        "score >= 80",
        "score >= 70",
        "score >= 60",
        "k >= len(ordered)",
    }
    required = [
        item
        for item in triage.results
        if item.contract.mutant.candidate.kind == "compare"
        and item.contract.mutant.candidate.after == "Gt"
        and item.contract.mutant.candidate.source_segment.strip() in required_segments
    ]
    assert len(required) == 5
    for item in required:
        assert item.label_contract == "REAL_GAP"

    clamp_contract_gaps = [
        item
        for item in triage.results
        if (
            item.mutant.candidate.kind,
            item.mutant.candidate.source_segment.strip(),
            item.mutant.candidate.after,
        )
        in {
            ("compare", "p < 0", "LtE"),
            ("compare", "p > 100", "GtE"),
        }
    ]
    assert len(clamp_contract_gaps) == 2
    assert all(item.label_contract == "REAL_GAP" for item in clamp_contract_gaps)
    assert any(
        "-0.0" in item.contract.winning_test.source for item in clamp_contract_gaps
    )
    assert any(
        "100.0" in item.contract.winning_test.source for item in clamp_contract_gaps
    )

    expected_shielded = [
        item
        for item in triage.results
        if (
            item.mutant.candidate.kind,
            item.mutant.candidate.source_segment.strip(),
            item.mutant.candidate.after,
        )
        in {
            ("arithmetic", "len(ordered) * p / 100", "FloorDiv"),
        }
    ]
    assert len(expected_shielded) == 1
    assert len(triage.contract_shielded) == 1
    for item in expected_shielded:
        assert item.label_strict == "REAL_GAP"
        assert item.label_contract == "PROBABLE_EQUIVALENT"
        assert len(item.contract.attempts) == 4
        rejected = item.contract.attempts[0]
        assert rejected.outcome == "INVALID_CONTRACT"
        assert rejected.original is None
        assert rejected.contract_violations
        valid = item.contract.attempts[1:]
        assert all(attempt.original.status == "passed" for attempt in valid)
        assert all(
            attempt.mutant is not None and attempt.mutant.status == "passed"
            for attempt in valid
        )
    assert set(triage.probe_target_mutant_ids) == {
        item.mutant.candidate.id
        for item in triage.results
        if item.label_contract == "REAL_GAP"
    }

    summary = json.loads(
        (result.artifact_dir / "summary.json").read_text(encoding="utf-8")
    )
    assert summary["total_survivors"] == 21
    assert summary["real_gap_count_strict"] == 21
    assert summary["probable_equivalent_count_strict"] == 0
    assert summary["equivalent_rate_strict"] == 0.0
    assert summary["real_gap_count_contract"] == 20
    assert summary["probable_equivalent_count_contract"] == 1
    assert summary["equivalent_rate_contract"] == 1 / 21
    assert summary["invalid_contract_attempts"] == 1
    assert len(summary["contract_shielded"]) == 1
    assert len(summary["probe_target_mutant_ids"]) == 20
    assert "false-negative risk" in summary["contract_limitation"].lower()
    assert "hide a genuine behavioral gap" in summary["contract_limitation"]
    assert summary["triage_complete"] is True

    assert result.probe is not None
    probe = result.probe
    assert probe.total_targets == 20
    expected_sites = {
        (item.mutant.candidate.path, item.mutant.candidate.anchor.line)
        for item in triage.results
        if item.label_contract == "REAL_GAP"
    }
    assert probe.total_sites == len(expected_sites)
    assert probe.question_count == probe.total_sites
    assert probe.accounted_mutant_count == triage.real_gap_count_contract
    assert sum(item.survivor_count for item in probe.results) == 20
    assert sum(len(item.mutants) for item in probe.results) == 20
    assert len(
        {
            (item.grounding.path, item.grounding.start_line)
            for item in probe.results
        }
    ) == probe.total_sites
    assert probe.submitted_answer_count == 1
    assert probe.graded_answer_count == 1
    assert probe.complete is True
    questioned_ids = {
        mutant.mutant_id
        for request in probe_agent.question_requests
        for mutant in request.mutants
    }
    assert questioned_ids == set(triage.probe_target_mutant_ids)
    assert len(probe_agent.question_requests) == probe.total_sites
    assert len({request.site_id for request in probe_agent.question_requests}) == (
        probe.total_sites
    )
    strict_only_ids = {
        item.mutant.candidate.id for item in triage.contract_shielded
    }
    assert questioned_ids.isdisjoint(strict_only_ids)
    assert all(
        mutant.evidence.original_execution.status == "passed"
        and mutant.evidence.mutant_execution.status in {"failed", "timed_out"}
        for item in probe.results
        for mutant in item.mutants
    )
    assert all(
        item.grounding.authored_lines
        and all(
            line.commit and line.author_date != "unknown"
            for line in item.grounding.authored_lines
        )
        for item in probe.results
    )
    graded = [item for item in probe.results if item.assessment is not None]
    assert len(graded) == 1
    for item in graded:
        assert item.assessment.citations
        assert len(item.assessment.citations) == item.survivor_count
        expected_citations = {
            (
                mutant.evidence.triage_artifact_ref,
                mutant.evidence.failing_assertion.message,
            )
            for mutant in item.mutants
        }
        assert {
            (citation.artifact_ref, citation.message)
            for citation in item.assessment.citations
        } == expected_citations

    assert result.report is not None
    report = result.report
    assert report.unverified_place_count == probe.total_sites
    assert report.question_count == probe.total_sites
    assert sum(place.survivor_count for place in report.places) == 20
    assert len(report.deliberately_not_asked) == 1
    assert report.equivalent_rate_strict == 0.0
    assert report.equivalent_rate_contract == 1 / 21
    report_payload = json.loads(
        (result.artifact_dir / "report" / "report.json").read_text(
            encoding="utf-8"
        )
    )
    assert report_payload["schema_version"] == "2.0"
    assert len(report_payload["places"]) == probe.total_sites
    assert sum(place["survivor_count"] for place in report_payload["places"]) == 20
    assert sum(len(place["mutants"]) for place in report_payload["places"]) == 20
    assert len(report_payload["deliberately_not_asked"]) == 1
    assert (result.artifact_dir / "report" / "report.md").exists()
