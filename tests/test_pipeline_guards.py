from __future__ import annotations

import json

import pytest

from fencepost.models import ExecutionResult, MutantResult, MutationCandidate, SourceSpan
from fencepost.pipeline import PipelineError, _raise_if_initial_mutants_all_broken


def _broken_result(index: int) -> MutantResult:
    candidate = MutationCandidate(
        id=str(index),
        path="gradebook/analytics.py",
        anchor=SourceSpan(1, 0, 1, 1),
        ast_path=(),
        kind="compare",
        before="GtE",
        after="Gt",
        source_segment="score >= 90",
    )
    return MutantResult(
        candidate=candidate,
        generated_anchor=SourceSpan(1, 0, 1, 1),
        execution=ExecutionResult(
            status="broken",
            exit_code=10,
            duration_seconds=0.2,
            stdout="",
            stderr="compile failed",
        ),
    )


def test_initial_all_broken_guard_stops_after_five(tmp_path) -> None:
    with pytest.raises(PipelineError, match="first 5 eligible mutants"):
        _raise_if_initial_mutants_all_broken(
            tmp_path, [_broken_result(index) for index in range(5)], candidate_count=40
        )

    diagnostic = json.loads((tmp_path / "all-broken.json").read_text(encoding="utf-8"))
    assert diagnostic["attempted_mutants"] == 5
    assert diagnostic["eligible_mutants"] == 40
