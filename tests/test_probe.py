from __future__ import annotations

import json
from dataclasses import replace

from fencepost.adversarial import CodexStructuredResponse
from fencepost.models import (
    AdversarialAttempt,
    AdversarialExecution,
    BlameLine,
    ContractShieldedResult,
    DualSurvivorTriageResult,
    ExecutionResult,
    FailureEvidence,
    GeneratedAdversarialTest,
    MutantResult,
    MutationCandidate,
    SourceSpan,
    SurvivorTriageResult,
    TriageModeSummary,
    TriageSummary,
)
from fencepost.probe import (
    CodexCliComprehensionProbeAgent,
    probe_site_id,
    run_probes,
)
from fencepost.report import build_report
from fencepost.triage import SurvivorContext
from tests.fakes import FixtureComprehensionProbeAgent


ORIGINAL = "def f(value):\n    return value >= 1\n"
MUTATED = "def f(value):\n    return value > 1\n"


def _records():
    candidate = MutationCandidate(
        id="contract-gap",
        path="pkg/analytics.py",
        anchor=SourceSpan(2, 11, 2, 21),
        ast_path=(),
        kind="compare",
        before="GtE",
        after="Gt",
        source_segment="value >= 1",
    )
    mutant = MutantResult(
        candidate=candidate,
        generated_anchor=SourceSpan(2, 11, 2, 20),
        execution=ExecutionResult("survived", 0, 0.1, "", ""),
    )
    test = GeneratedAdversarialTest(
        source="from pkg.analytics import f\n\ndef test_boundary():\n    assert f(1)\n",
        targeted_behavior="exact lower boundary",
        provider="fixture",
        model=None,
        response_id=None,
        generation_duration_seconds=0.0,
    )
    failure = FailureEvidence(
        nodeid="test_probe.py::test_boundary",
        kind="failure",
        message="assert False",
        detail="AssertionError",
    )
    original_execution = AdversarialExecution(
        "passed", 0, 0.01, "", "", tests_collected=1
    )
    mutant_execution = AdversarialExecution(
        "failed", 1, 0.01, "", "", tests_collected=1, failure=failure
    )
    attempt = AdversarialAttempt(
        attempt=1,
        valid_attempt_number=1,
        generated_test=test,
        outcome="DISTINGUISHED",
        original=original_execution,
        mutant=mutant_execution,
    )
    strict_gap = SurvivorTriageResult(
        mode="STRICT",
        mutant=mutant,
        label="REAL_GAP",
        attempts=(attempt,),
        attempts_used=1,
        valid_attempts=1,
        invalid_attempts=0,
        winning_test=test,
        failure_evidence=failure,
    )
    contract_gap = SurvivorTriageResult(
        mode="CONTRACT",
        mutant=mutant,
        label="REAL_GAP",
        attempts=(attempt,),
        attempts_used=1,
        valid_attempts=1,
        invalid_attempts=0,
        winning_test=test,
        failure_evidence=failure,
    )

    shielded_candidate = MutationCandidate(
        id="strict-only",
        path="pkg/analytics.py",
        anchor=SourceSpan(2, 11, 2, 21),
        ast_path=(),
        kind="arithmetic",
        before="Div",
        after="FloorDiv",
        source_segment="value >= 1",
    )
    shielded_mutant = MutantResult(
        candidate=shielded_candidate,
        generated_anchor=SourceSpan(2, 11, 2, 20),
        execution=ExecutionResult("survived", 0, 0.1, "", ""),
    )
    strict_only = SurvivorTriageResult(
        mode="STRICT",
        mutant=shielded_mutant,
        label="REAL_GAP",
        attempts=(attempt,),
        attempts_used=1,
        valid_attempts=1,
        invalid_attempts=0,
        winning_test=test,
        failure_evidence=failure,
    )
    contract_equivalent = SurvivorTriageResult(
        mode="CONTRACT",
        mutant=shielded_mutant,
        label="PROBABLE_EQUIVALENT",
        attempts=(),
        attempts_used=3,
        valid_attempts=3,
        invalid_attempts=0,
        winning_test=None,
        failure_evidence=None,
    )
    strict_summary = TriageModeSummary(
        mode="STRICT",
        total_survivors=2,
        selected_survivor_count=2,
        real_gap_count=2,
        probable_equivalent_count=0,
        unresolved_count=0,
        equivalent_rate=0.0,
        triage_complete=True,
        total_attempts=2,
        valid_attempts=2,
        invalid_original_attempts=0,
        invalid_contract_attempts=0,
        generator_call_count=2,
        generator_wall_clock_seconds=0.0,
        triage_wall_clock_seconds=0.0,
        results=(strict_gap, strict_only),
    )
    contract_summary = TriageModeSummary(
        mode="CONTRACT",
        total_survivors=2,
        selected_survivor_count=2,
        real_gap_count=1,
        probable_equivalent_count=1,
        unresolved_count=0,
        equivalent_rate=0.5,
        triage_complete=True,
        total_attempts=4,
        valid_attempts=4,
        invalid_original_attempts=0,
        invalid_contract_attempts=0,
        generator_call_count=4,
        generator_wall_clock_seconds=0.0,
        triage_wall_clock_seconds=0.0,
        results=(contract_gap, contract_equivalent),
    )
    pairs = (
        DualSurvivorTriageResult(
            mutant=mutant,
            label_strict="REAL_GAP",
            label_contract="REAL_GAP",
            strict=strict_gap,
            contract=contract_gap,
        ),
        DualSurvivorTriageResult(
            mutant=shielded_mutant,
            label_strict="REAL_GAP",
            label_contract="PROBABLE_EQUIVALENT",
            strict=strict_only,
            contract=contract_equivalent,
        ),
    )
    triage = TriageSummary(
        total_survivors=2,
        selected_survivor_count=2,
        real_gap_count_strict=2,
        probable_equivalent_count_strict=0,
        unresolved_count_strict=0,
        equivalent_rate_strict=0.0,
        real_gap_count_contract=1,
        probable_equivalent_count_contract=1,
        unresolved_count_contract=0,
        equivalent_rate_contract=0.5,
        invalid_contract_attempts=0,
        triage_complete=True,
        generator_call_count=6,
        generator_wall_clock_seconds=0.0,
        triage_wall_clock_seconds=0.0,
        strict=strict_summary,
        contract=contract_summary,
        results=pairs,
        contract_shielded=(
            ContractShieldedResult(
                mutant=shielded_mutant,
                label_strict="REAL_GAP",
                label_contract="PROBABLE_EQUIVALENT",
                strict_winning_test=test,
                strict_failure_evidence=failure,
                strict_killing_attempt=attempt,
            ),
        ),
        probe_target_mutant_ids=("contract-gap",),
        contract_rules={},
        contract_limitation="CONTRACT can hide a genuine type-only gap.",
    )
    contexts = (
        SurvivorContext(
            mutant=mutant,
            original_source=ORIGINAL,
            mutated_source=MUTATED,
            module_path="pkg.analytics",
            qualified_function_name="f",
            original_function=ORIGINAL.strip(),
            mutated_function=MUTATED.strip(),
            unified_diff="-    return value >= 1\n+    return value > 1",
        ),
        SurvivorContext(
            mutant=shielded_mutant,
            original_source=ORIGINAL,
            mutated_source=MUTATED,
            module_path="pkg.analytics",
            qualified_function_name="f",
            original_function=ORIGINAL.strip(),
            mutated_function=MUTATED.strip(),
            unified_diff="-    return value >= 1\n+    return value > 1",
        ),
    )
    blame = {
        "pkg/analytics.py": {
            2: BlameLine(
                path="pkg/analytics.py",
                line=2,
                commit="4a3f000000000000000000000000000000000000",
                author_name="Diego Ramos",
                author_email="student@example.edu",
                author_date="2026-07-07",
                summary="implement boundary",
                is_student=True,
            )
        }
    }
    return triage, contexts, blame


def _records_with_two_gaps_at_one_site():
    """Add a second execution-decided gap without changing its source site."""
    triage, contexts, blame = _records()
    first = triage.results[0]
    second_candidate = replace(
        first.mutant.candidate,
        id="contract-gap-2",
        anchor=SourceSpan(2, 20, 2, 21),
        kind="numeric_boundary",
        before="1",
        after="2",
        source_segment="1",
    )
    second_mutant = replace(
        first.mutant,
        candidate=second_candidate,
        generated_anchor=SourceSpan(2, 20, 2, 21),
    )
    second_strict = replace(first.strict, mutant=second_mutant)
    second_contract = replace(first.contract, mutant=second_mutant)
    second_pair = replace(
        first,
        mutant=second_mutant,
        strict=second_strict,
        contract=second_contract,
    )
    second_mutated_source = "def f(value):\n    return value >= 2\n"
    second_context = replace(
        contexts[0],
        mutant=second_mutant,
        mutated_source=second_mutated_source,
        mutated_function=second_mutated_source.strip(),
        unified_diff="-    return value >= 1\n+    return value >= 2",
    )
    triage = replace(
        triage,
        total_survivors=3,
        selected_survivor_count=3,
        real_gap_count_strict=3,
        real_gap_count_contract=2,
        results=(first, second_pair, triage.results[1]),
        probe_target_mutant_ids=("contract-gap", "contract-gap-2"),
    )
    return triage, (contexts[0], second_context, contexts[1]), blame


def test_probe_targets_contract_gaps_and_grades_with_execution_citation(tmp_path) -> None:
    triage, contexts, blame = _records_with_two_gaps_at_one_site()
    agent = FixtureComprehensionProbeAgent()
    site_id = probe_site_id("pkg/analytics.py", 2)
    summary = run_probes(
        triage,
        contexts,
        blame=blame,
        agent=agent,
        answers={site_id: "I don't know"},
        artifact_dir=tmp_path,
    )

    assert len(agent.question_requests) == 1
    assert agent.question_requests[0].site_id == site_id
    assert {mutant.mutant_id for mutant in agent.question_requests[0].mutants} == {
        "contract-gap",
        "contract-gap-2",
    }
    assert all(
        mutant.mutant_id != "strict-only"
        for request in agent.question_requests
        for mutant in request.mutants
    )
    assert summary.total_targets == 2
    assert summary.total_sites == 1
    assert summary.accounted_mutant_count == 2
    assert summary.question_count == 1
    assert summary.graded_answer_count == 1
    result = summary.results[0]
    assert result.status == "GRADED"
    assert result.site_id == site_id
    assert result.survivor_count == 2
    assert len(result.mutants) == 2
    assert result.assessment is not None
    assert result.assessment.verdict == "INSUFFICIENT"
    assert len(result.assessment.citations) == result.survivor_count
    expected_citations = {
        (
            mutant.evidence.failing_assertion.message,
            mutant.evidence.triage_artifact_ref,
        )
        for mutant in result.mutants
    }
    assert {
        (citation.message, citation.artifact_ref)
        for citation in result.assessment.citations
    } == expected_citations

    report = build_report(
        commit="fixture-commit",
        student_email="student@example.edu",
        student_name="Diego Ramos",
        triage=triage,
        probe=summary,
        contexts=contexts,
        artifact_dir=tmp_path,
    )
    assert report.unverified_place_count == 1
    assert report.question_count == 1
    assert sum(place.survivor_count for place in report.places) == 2
    assert len(report.deliberately_not_asked) == 1
    assert report.deliberately_not_asked[0].mutant_id == "strict-only"
    payload = json.loads(
        (tmp_path / "report" / "report.json").read_text(encoding="utf-8")
    )
    assert payload["schema_version"] == "2.0"
    assert payload["places"][0]["survivor_count"] == 2
    assert len(payload["places"][0]["mutants"]) == 2
    assert payload["places"][0]["assessment"]["citations"][0]["message"] == "assert False"
    rendered = (tmp_path / "report" / "report.md").read_text(encoding="utf-8")
    assert "Deliberately not asked" in rendered
    assert "CONTRACT limitation" in rendered
    assert "```python\n   2 |     return value >= 1\n```" in rendered
    assert "`value >= 1`" in rendered
    assert "&gt;" not in rendered
    assert r"\." not in rendered
    assert result.question is not None
    assert rendered.count(result.question.question_text) == 1


def test_codex_probe_agent_uses_shared_structured_client(tmp_path) -> None:
    triage, contexts, blame = _records_with_two_gaps_at_one_site()

    class SharedClient:
        model = "gpt-5.6-terra"

        def __init__(self):
            self.calls = []

        def run(self, *, prompt, schema):
            self.calls.append((prompt, schema))
            if schema["required"] == ["question_prompt"]:
                payload = {
                    "question_prompt": "What observable boundary behavior changes, and why?"
                }
            else:
                payload = {
                    "verdict": "UNDERSTANDS",
                    "feedback": "The answer identifies the changed boundary behavior.",
                    "evidence_explanation": "It agrees with the supplied failing assertion.",
                }
            return CodexStructuredResponse(
                payload=payload,
                response_id="fixture-thread",
                duration_seconds=0.01,
                input_tokens=10,
                output_tokens=5,
            )

    client = SharedClient()
    agent = CodexCliComprehensionProbeAgent(
        model="gpt-5.6-terra", client=client
    )
    summary = run_probes(
        triage,
        contexts,
        blame=blame,
        agent=agent,
        answers={
            probe_site_id("pkg/analytics.py", 2): (
                "The equality boundary no longer passes."
            )
        },
        artifact_dir=tmp_path,
    )

    assert len(client.calls) == 2
    assert summary.graded_answer_count == 1
    assert summary.results[0].question is not None
    assert summary.results[0].question.model == "gpt-5.6-terra"
    assert "surviving_mutants" in client.calls[0][0]
    assert "surviving_mutants" in client.calls[1][0]
    assert "contract-gap-2" in client.calls[0][0]
    assert "contract-gap-2" in client.calls[1][0]


def test_codex_probe_rejects_question_that_repeats_report_grounding(tmp_path) -> None:
    triage, contexts, blame = _records()

    class RepeatingClient:
        model = "gpt-5.6-terra"

        def run(self, *, prompt, schema):
            return CodexStructuredResponse(
                payload={
                    "question_prompt": (
                        "In commit 4a3f000 on 2026-07-07, what changes on line 2?"
                    )
                },
                response_id="fixture-thread",
                duration_seconds=0.01,
                input_tokens=10,
                output_tokens=5,
            )

    agent = CodexCliComprehensionProbeAgent(
        model="gpt-5.6-terra", client=RepeatingClient()
    )
    summary = run_probes(
        triage,
        contexts,
        blame=blame,
        agent=agent,
        answers=None,
        artifact_dir=tmp_path,
    )

    assert summary.question_count == 0
    assert summary.failed_question_count == 1
    assert summary.results[0].status == "QUESTION_FAILED"
    assert summary.results[0].question is None
