"""The supplied demo is the non-negotiable stage 1-4 acceptance fixture."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fencepost import RunConfig, run_analysis
from fencepost.mutation import enumerate_candidates


ROOT = Path(__file__).resolve().parents[2]


def _compare_status(result, source_segment: str, after: str) -> str:
    matches = [
        mutant.execution.status
        for mutant in result.mutant_results
        if mutant.candidate.kind == "compare"
        and mutant.candidate.source_segment.strip() == source_segment
        and mutant.candidate.after == after
    ]
    assert len(matches) == 1, source_segment
    return matches[0]


def test_demo_pipeline_reproduces_required_classifications(tmp_path: Path) -> None:
    repo = tmp_path / "student-repo"
    subprocess.run(
        [sys.executable, str(ROOT / "demo" / "build_demo_repo.py"), str(repo)],
        check=True,
        cwd=ROOT,
    )
    analytics_source = (repo / "gradebook" / "analytics.py").read_text(encoding="utf-8")
    assert len(enumerate_candidates(analytics_source, "gradebook/analytics.py")) == 56

    result = run_analysis(
        RunConfig(
            repo=repo,
            student_email="d.ramos@alumnos.ejemplo.edu",
            artifact_dir=tmp_path / "artifact",
        )
    )

    for score in (90, 80, 70, 60):
        assert _compare_status(result, f"score >= {score}", "Gt") == "survived"
    assert _compare_status(result, "k >= len(ordered)", "Gt") == "survived"
    assert _compare_status(result, "p < 0", "LtE") == "survived"
    assert _compare_status(result, "p > 100", "GtE") == "survived"
    assert _compare_status(result, "s > target", "GtE") == "killed"

    top_n = [
        mutant.execution.status
        for mutant in result.mutant_results
        if mutant.candidate.kind == "slice_boundary"
        and mutant.candidate.source_segment.strip() == "n"
        and mutant.candidate.after == "n + 1"
    ]
    assert top_n == ["killed"]
    # Fencepost mutates production code, never pytest assertions. It finds 56 raw
    # AST candidates in analytics.py. Five candidates sit
    # on the deliberately uncovered percentile-guard body or return-D body; the
    # remaining 51 have both student authorship and submitted-suite coverage.
    assert result.mutant_count == 51
    assert {mutant.candidate.path for mutant in result.mutant_results} == {
        "gradebook/analytics.py"
    }
    assert result.elapsed_seconds > 0
    assert (result.artifact_dir / "summary.json").exists()
