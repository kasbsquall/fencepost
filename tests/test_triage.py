from __future__ import annotations

from dataclasses import dataclass

from fencepost.adversarial import AdversarialGeneratorError
from fencepost.models import (
    AdversarialExecution,
    ExecutionResult,
    FailureEvidence,
    GeneratedAdversarialTest,
    MutantResult,
    MutationCandidate,
    SourceSpan,
    TriageConfig,
    TriageJobResult,
)
from fencepost.mutation import enumerate_candidates, generate_mutation
from fencepost.sandbox import SandboxError
from fencepost.triage import (
    SurvivorContext,
    build_survivor_context,
    triage_survivors,
)


def _context(mutant_id: str) -> SurvivorContext:
    mutant = MutantResult(
        candidate=MutationCandidate(
            id=mutant_id,
            path="pkg/analytics.py",
            anchor=SourceSpan(1, 0, 1, 1),
            ast_path=(),
            kind="compare",
            before="GtE",
            after="Gt",
            source_segment="value >= 1",
        ),
        generated_anchor=SourceSpan(1, 0, 1, 1),
        execution=ExecutionResult("survived", 0, 0.1, "", ""),
    )
    return SurvivorContext(
        mutant=mutant,
        original_source="def f(value):\n    return value >= 1\n",
        mutated_source="def f(value):\n    return value > 1\n",
        module_path="pkg.analytics",
        qualified_function_name="f",
        original_function="def f(value):\n    return value >= 1",
        mutated_function="def f(value):\n    return value > 1",
        unified_diff="- value >= 1\n+ value > 1",
    )


def _execution(status: str, *, failure: bool = False) -> AdversarialExecution:
    evidence = (
        FailureEvidence(
            nodeid="test_adversarial::test_boundary",
            kind="failure",
            message="assert 'B' == 'A'",
            detail="AssertionError",
        )
        if failure
        else None
    )
    return AdversarialExecution(
        status=status,
        exit_code=0 if status == "passed" else 1,
        duration_seconds=0.01,
        stdout="",
        stderr="",
        tests_collected=1,
        failure=evidence,
    )


@dataclass
class FakeGenerator:
    broken: bool = False

    def generate(self, request):
        source = "not valid python !" if self.broken else "def test_generated():\n    assert True\n"
        return GeneratedAdversarialTest(
            source=source,
            targeted_behavior="fixture behavior",
            provider="fake",
            model=None,
            response_id=None,
            generation_duration_seconds=0.0,
        )


class FakeSession:
    def __init__(self, scripts):
        self.scripts = {key: list(value) for key, value in scripts.items()}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def run_round(self, round_id, jobs):
        results = {}
        for job in jobs:
            mutant_id = next(key for key in self.scripts if job.id.startswith(key))
            outcome = self.scripts[mutant_id].pop(0)
            if outcome == "INVALID_ON_ORIGINAL":
                original = _execution("failed", failure=True)
                mutant = None
            elif outcome == "DISTINGUISHED":
                original = _execution("passed")
                mutant = _execution("failed", failure=True)
            else:
                original = _execution("passed")
                mutant = _execution("passed")
            results[job.id] = TriageJobResult(
                id=job.id,
                outcome=outcome,
                original=original,
                mutant=mutant,
            )
        return results


class FakeSandbox:
    def __init__(self, scripts, *, infrastructure_failure=False):
        self.scripts = scripts
        self.infrastructure_failure = infrastructure_failure

    @staticmethod
    def import_roots(baseline_tree):
        return (".",)

    def triage_session(self, *args, **kwargs):
        if self.infrastructure_failure:
            raise SandboxError("session unavailable")
        return FakeSession(self.scripts)


class FailingGenerator:
    def generate(self, request):
        raise AdversarialGeneratorError("model unavailable")


def _triage(tmp_path, contexts, scripts, *, generator=None, sandbox=None):
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    return triage_survivors(
        contexts,
        generator=generator or FakeGenerator(),
        sandbox=sandbox or FakeSandbox(scripts),
        baseline_tree=baseline,
        artifact_dir=tmp_path / "artifact",
        config=TriageConfig(valid_attempts=3, invalid_retry_limit=3),
        workers=2,
    )


def test_context_uses_original_anchor_but_mutated_unparsed_function() -> None:
    source = (
        "def letter_grade(score):\n"
        "    if score >= 90:\n"
        "        return 'A'\n"
        "    return 'B'\n"
    )
    candidate = next(
        item
        for item in enumerate_candidates(source, "gradebook/analytics.py")
        if item.kind == "compare" and item.after == "Gt"
    )
    generated = generate_mutation(source, candidate)
    mutant = MutantResult(
        candidate=candidate,
        generated_anchor=generated.generated_anchor,
        execution=ExecutionResult("survived", 0, 0.1, "", ""),
    )

    context = build_survivor_context(
        mutant,
        original_source=source,
        mutated_source=generated.source,
        import_roots=(".",),
    )

    assert context.module_path == "gradebook.analytics"
    assert context.qualified_function_name == "letter_grade"
    assert "score >= 90" in context.original_function
    assert "score > 90" in context.mutated_function
    assert "-    if score >= 90:" in context.unified_diff
    assert "+    if score > 90:" in context.unified_diff


def test_three_consecutive_invalid_tests_become_unresolved(tmp_path) -> None:
    context = _context("invalid-mutant")
    summary = _triage(
        tmp_path,
        [context],
        {"invalid-mutant": ["INVALID_ON_ORIGINAL"] * 3},
        generator=FakeGenerator(broken=True),
    )

    result = summary.results[0]
    assert result.label == "UNRESOLVED"
    assert result.valid_attempts == 0
    assert result.invalid_attempts == 3
    assert summary.unresolved_count == 1
    assert summary.probable_equivalent_count == 0
    assert summary.equivalent_rate is None
    assert summary.triage_complete is True


def test_invalid_counter_resets_after_each_valid_attempt(tmp_path) -> None:
    context = _context("equivalent-mutant")
    outcomes = [
        "INVALID_ON_ORIGINAL",
        "NOT_DISTINGUISHED",
        "INVALID_ON_ORIGINAL",
        "NOT_DISTINGUISHED",
        "INVALID_ON_ORIGINAL",
        "NOT_DISTINGUISHED",
    ]
    summary = _triage(
        tmp_path, [context], {"equivalent-mutant": outcomes}
    )

    result = summary.results[0]
    assert result.label == "PROBABLE_EQUIVALENT"
    assert result.valid_attempts == 3
    assert result.invalid_attempts == 3
    assert result.attempts_used == 6
    assert summary.equivalent_rate == 1.0


def test_real_gap_requires_original_pass_and_mutant_failure_pair(tmp_path) -> None:
    context = _context("gap-mutant")
    summary = _triage(
        tmp_path, [context], {"gap-mutant": ["DISTINGUISHED"]}
    )

    result = summary.results[0]
    assert result.label == "REAL_GAP"
    assert result.winning_test is not None
    assert result.attempts[0].original.status == "passed"
    assert result.attempts[0].mutant.status == "failed"
    assert result.failure_evidence is not None
    assert summary.equivalent_rate == 0.0


def test_unresolved_survivors_are_excluded_from_equivalent_rate(tmp_path) -> None:
    gap = _context("gap-mutant")
    unresolved = _context("unresolved-mutant")
    summary = _triage(
        tmp_path,
        [gap, unresolved],
        {
            "gap-mutant": ["DISTINGUISHED"],
            "unresolved-mutant": ["INVALID_ON_ORIGINAL"] * 3,
        },
    )

    assert summary.total_survivors == 2
    assert summary.real_gap_count == 1
    assert summary.probable_equivalent_count == 0
    assert summary.unresolved_count == 1
    assert summary.equivalent_rate == 0.0


def test_sandbox_failure_makes_run_incomplete_and_rate_null(tmp_path) -> None:
    context = _context("infra-mutant")
    summary = _triage(
        tmp_path,
        [context],
        {},
        sandbox=FakeSandbox({}, infrastructure_failure=True),
    )

    assert summary.results[0].label == "UNRESOLVED"
    assert summary.triage_complete is False
    assert summary.equivalent_rate is None


def test_generator_failure_is_unresolved_never_equivalent(tmp_path) -> None:
    context = _context("generator-mutant")
    summary = _triage(
        tmp_path,
        [context],
        {},
        generator=FailingGenerator(),
    )

    result = summary.results[0]
    assert result.label == "UNRESOLVED"
    assert result.attempts_used == 0
    assert "model unavailable" in result.unresolved_reason
    assert summary.probable_equivalent_count == 0
    assert summary.equivalent_rate is None
