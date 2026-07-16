"""Hermetic Stage 5 gate: model seam is fake, every label is Docker-decided."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fencepost import RunConfig, TriageConfig, run_analysis
from tests.fakes import FixtureAdversarialTestGenerator


ROOT = Path(__file__).resolve().parents[2]


def test_demo_survivors_are_triaged_with_execution_evidence(tmp_path: Path) -> None:
    repo = tmp_path / "student-repo"
    subprocess.run(
        [sys.executable, str(ROOT / "demo" / "build_demo_repo.py"), str(repo)],
        check=True,
        cwd=ROOT,
    )
    generator = FixtureAdversarialTestGenerator()
    result = run_analysis(
        RunConfig(
            repo=repo,
            student_email="d.ramos@alumnos.ejemplo.edu",
            artifact_dir=tmp_path / "artifact",
        ),
        adversarial_generator=generator,
        triage_config=TriageConfig(valid_attempts=3, invalid_retry_limit=3),
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
