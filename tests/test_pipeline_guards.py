from __future__ import annotations

import json
from dataclasses import replace

import pytest

from fencepost.models import (
    BlameLine,
    AttributionIdentity,
    ExecutionResult,
    MutantResult,
    MutationCandidate,
    SourceSpan,
)
from fencepost.pipeline import (
    PipelineError,
    _candidate_inventory,
    _raise_if_initial_mutants_all_broken,
)
from fencepost.repository import SourceFile


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


def test_authored_line_coverage_counts_unique_mutatable_source_lines() -> None:
    source = SourceFile(
        path="pkg/logic.py",
        text=(
            "def f(value):\n"
            "    if value > 0:\n"
            "        return value + 1\n"
            "    return 0\n"
        ),
        sha256="fixture",
    )
    blame = {
        source.path: {
            line: BlameLine(
                path=source.path,
                line=line,
                commit="a" * 40,
                author_name="Student",
                author_email="student@example.edu",
                author_date="2026-07-01",
                summary="implement logic",
                is_student=True,
            )
            for line in range(1, 5)
        }
    }

    eligible, coverage, functions, exclusions = _candidate_inventory(
        (source,), blame, {source.path: (2,)}
    )

    assert coverage.authored_mutatable_line_count == 3
    assert coverage.covered_authored_mutatable_line_count == 1
    assert coverage.rate == pytest.approx(1 / 3)
    assert coverage.minimum_rate == 0.5
    assert coverage.sufficient_for_assessment is False
    assert eligible
    assert set(functions.values()) == {"f"}
    assert exclusions == ()

    coauthored = {
        source.path: dict(blame[source.path])
    }
    coauthored[source.path][2] = replace(
        coauthored[source.path][2],
        co_authors=(AttributionIdentity(name="Partner", email="partner@example.edu"),),
    )
    excluded_eligible, excluded_coverage, _, exclusions = _candidate_inventory(
        (source,), coauthored, {source.path: (2,)}
    )
    assert all(item.candidate.anchor.line != 2 for item in excluded_eligible)
    assert excluded_coverage.authored_mutatable_line_count == 2
    assert exclusions[0].reason == "co_authored_commit"
    assert exclusions[0].co_authors[0].email == "partner@example.edu"
