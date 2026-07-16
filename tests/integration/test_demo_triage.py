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

    assert len(stage4_survivors) == 15
    assert triage.total_survivors == 15
    assert triaged_ids == stage4_survivors
    assert triaged_ids.isdisjoint(stage4_killed)
    assert triage.real_gap_count == 5
    assert triage.probable_equivalent_count == 10
    assert triage.unresolved_count == 0
    assert triage.equivalent_rate == 10 / 15
    assert triage.triage_complete is True
    assert {item.label for item in triage.results} == {
        "REAL_GAP",
        "PROBABLE_EQUIVALENT",
    }

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
        if item.mutant.candidate.kind == "compare"
        and item.mutant.candidate.after == "Gt"
        and item.mutant.candidate.source_segment.strip() in required_segments
    ]
    assert len(required) == 5
    for item in required:
        assert item.label == "REAL_GAP"
        assert item.winning_test is not None
        assert item.failure_evidence is not None
        winning = item.attempts[-1]
        assert winning.original.status == "passed"
        assert winning.mutant is not None
        assert winning.mutant.status in {"failed", "timed_out"}

    summary = json.loads(
        (result.artifact_dir / "summary.json").read_text(encoding="utf-8")
    )
    assert summary["total_survivors"] == 15
    assert summary["real_gap_count"] == 5
    assert summary["probable_equivalent_count"] == 10
    assert summary["unresolved_count"] == 0
    assert summary["equivalent_rate"] == 10 / 15
    assert summary["triage_complete"] is True
