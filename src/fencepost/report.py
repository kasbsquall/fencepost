"""Stage 7: stable execution-traceable report artifacts for instructors and UIs."""

from __future__ import annotations

import ast
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Mapping, Sequence

from .models import (
    AuthoredLineCoverage,
    ContractShieldedReportItem,
    FencepostReport,
    FunctionAssessment,
    MutantResult,
    MutationOutcomeSummary,
    ProbeSummary,
    ReportFunctionGroup,
    TriageSummary,
    json_value,
)
from .probe import source_span_segment
from .triage import SurvivorContext


REPORT_SCHEMA_VERSION = "2.0"

_COMMIT_CLAIM_RE = re.compile(
    r"\b(?:fix|fixed|prevent|handle|guard|correct|resolve|repair|ensure|support)\b",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_RANKING_STOPWORDS = frozenset(
    {"a", "an", "and", "for", "in", "of", "on", "the", "to", "when", "with"}
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_value(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_report(
    *,
    commit: str,
    student_email: str,
    student_name: str | None,
    triage: TriageSummary,
    probe: ProbeSummary,
    contexts: Sequence[SurvivorContext],
    submitted_suite_tests_passed: int | None,
    authored_line_coverage: AuthoredLineCoverage,
    mutant_results: Sequence[MutantResult],
    function_by_mutant_id: Mapping[str, str],
    artifact_dir: Path,
) -> FencepostReport:
    """Create the UI-ready JSON contract and its instructor-facing Markdown view."""
    context_by_id = {
        context.mutant.candidate.id: context for context in contexts
    }
    shielded: list[ContractShieldedReportItem] = []
    for item in triage.contract_shielded:
        candidate_id = item.mutant.candidate.id
        context = context_by_id[candidate_id]
        attempt = item.strict_killing_attempt.attempt
        shielded.append(
            ContractShieldedReportItem(
                mutant_id=candidate_id,
                path=item.mutant.candidate.path,
                line=item.mutant.candidate.anchor.line,
                original_segment=item.mutant.candidate.source_segment.strip(),
                mutated_segment=source_span_segment(
                    context.mutated_source, item.mutant.generated_anchor
                ),
                reason=(
                    "STRICT execution found a technical distinction, but CONTRACT "
                    "execution did not find a caller-conforming distinction. Fencepost "
                    "therefore withholds this question from the student."
                ),
                plain_language_reason=_plain_shield_reason(
                    item.strict_winning_test.source
                ),
                strict_test=item.strict_winning_test,
                strict_failure_evidence=item.strict_failure_evidence,
                artifact_refs=(
                    f"triage/strict/{candidate_id}/attempt-{attempt:02d}/attempt.json",
                    f"triage/contract/{candidate_id}/result.json",
                ),
            )
        )

    mutation_summary = MutationOutcomeSummary(
        total_mutants=len(mutant_results),
        killed_by_submitted_tests=sum(
            item.execution.status == "killed" for item in mutant_results
        ),
        survived_submitted_tests=sum(
            item.execution.status == "survived" for item in mutant_results
        ),
        broken_mutants=sum(
            item.execution.status in {"broken", "infrastructure_error"}
            for item in mutant_results
        ),
    )
    function_assessments = _function_assessments(
        mutant_results,
        function_by_mutant_id=function_by_mutant_id,
        triage=triage,
        probe=probe,
    )
    function_groups = _ranked_function_groups(probe)

    report = FencepostReport(
        schema_version=REPORT_SCHEMA_VERSION,
        title="Fencepost comprehension report",
        formative_notice=(
            "This report is formative and advisory. It identifies behavior changes "
            "the submitted tests did not distinguish; it is not a verdict, accusation, "
            "or standalone score. An instructor should review the evidence and decide "
            "whether a conversation would be useful."
        ),
        student_name=student_name,
        student_email=student_email,
        repository_commit=commit,
        submitted_suite_status="PASSED",
        submitted_suite_tests_passed=submitted_suite_tests_passed,
        baseline_artifact_ref="baseline/result.json",
        authored_line_coverage=authored_line_coverage,
        mutation_summary=mutation_summary,
        function_assessments=function_assessments,
        function_groups=function_groups,
        conversation_count=len(function_groups),
        question_mutant_count=probe.eligible_target_count,
        not_questioned_mutant_count=max(
            0,
            mutation_summary.survived_submitted_tests
            - probe.eligible_target_count,
        ),
        unverified_place_count=probe.total_sites,
        question_count=probe.question_count,
        submitted_answer_count=probe.submitted_answer_count,
        graded_answer_count=probe.graded_answer_count,
        real_gap_count_strict=triage.real_gap_count_strict,
        probable_equivalent_count_strict=triage.probable_equivalent_count_strict,
        unresolved_count_strict=triage.unresolved_count_strict,
        equivalent_rate_strict=triage.equivalent_rate_strict,
        real_gap_count_contract=triage.real_gap_count_contract,
        probable_equivalent_count_contract=triage.probable_equivalent_count_contract,
        unresolved_count_contract=triage.unresolved_count_contract,
        equivalent_rate_contract=triage.equivalent_rate_contract,
        contract_limitation=triage.contract_limitation,
        places=probe.results,
        deliberately_not_asked=tuple(shielded),
        pedagogically_not_asked=probe.pedagogically_withheld,
        traceability_artifacts=(
            "run.json",
            "baseline/result.json",
            "selection.json",
            "triage/summary.json",
            "probe/summary.json",
        ),
        complete=triage.triage_complete and probe.complete,
    )
    report_root = artifact_dir / "report"
    _write_json(report_root / "report.json", report)
    (report_root / "report.md").write_text(
        render_report_markdown(report), encoding="utf-8"
    )
    return report


def _plain_shield_reason(test_source: str) -> str:
    """Explain a technical-only STRICT witness before showing its code."""
    tree = ast.parse(test_source)
    if any(isinstance(node, ast.ClassDef) for node in ast.walk(tree)):
        return (
            "We found a way to break this, but only by feeding the function a fake "
            "object no ordinary caller would write. That is not a fair question, so "
            "we dropped it."
        )
    if any(
        isinstance(node, (ast.Is, ast.IsNot))
        or (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"id", "isinstance", "type"}
        )
        for node in ast.walk(tree)
    ):
        return (
            "We found a technical difference only by inspecting object identity or "
            "type. That is not a fair question about the function's ordinary result, "
            "so we dropped it."
        )
    return (
        "We found a technical way to distinguish this change, but it falls outside "
        "the plain-caller contract used for student questions. We dropped it rather "
        "than ask about an artificial edge case."
    )


def _function_assessments(
    mutant_results: Sequence[MutantResult],
    *,
    function_by_mutant_id: Mapping[str, str],
    triage: TriageSummary,
    probe: ProbeSummary,
) -> tuple[FunctionAssessment, ...]:
    grouped: dict[tuple[str, str], list[MutantResult]] = defaultdict(list)
    for mutant in mutant_results:
        function_name = function_by_mutant_id.get(mutant.candidate.id, "<unknown>")
        grouped[(mutant.candidate.path, function_name)].append(mutant)
    contract_gap_ids = {
        item.mutant.candidate.id
        for item in triage.results
        if item.label_contract == "REAL_GAP"
    }
    question_sites: dict[tuple[str, str], set[str]] = defaultdict(set)
    for site in probe.results:
        if not site.mutants:
            continue
        key = (
            site.grounding.path,
            site.mutants[0].qualified_function_name,
        )
        question_sites[key].add(site.site_id)

    results = []
    for (path, function_name), mutants in grouped.items():
        killed = sum(item.execution.status == "killed" for item in mutants)
        survived = sum(item.execution.status == "survived" for item in mutants)
        broken = sum(
            item.execution.status in {"broken", "infrastructure_error"}
            for item in mutants
        )
        gap_count = sum(
            item.candidate.id in contract_gap_ids for item in mutants
        )
        if mutants and killed == len(mutants):
            status = "CLEAN"
        elif gap_count:
            status = "GAPS_FOUND"
        elif broken:
            status = "INCOMPLETE"
        elif survived:
            status = "NO_FAIR_QUESTION"
        else:
            status = "MIXED"
        results.append(
            FunctionAssessment(
                path=path,
                qualified_function_name=function_name,
                status=status,
                total_mutants=len(mutants),
                killed_by_submitted_tests=killed,
                survived_submitted_tests=survived,
                broken_mutants=broken,
                contract_real_gap_mutants=gap_count,
                question_site_count=len(question_sites[(path, function_name)]),
                artifact_refs=tuple(
                    f"mutants/{item.candidate.id}/result.json" for item in mutants
                ),
            )
        )
    return tuple(
        sorted(
            results,
            key=lambda item: (
                item.status != "CLEAN",
                item.path,
                item.qualified_function_name,
            ),
        )
    )


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(value.casefold())
        if token not in _RANKING_STOPWORDS and len(token) > 1
    }


def _group_ranking(site_results) -> tuple[tuple[int, int, int, int], tuple[str, ...], str | None]:
    summaries: list[tuple[str, str]] = []
    evidence_parts = []
    for site in site_results:
        for line in site.grounding.authored_lines:
            if line.commit_summary:
                summaries.append((line.commit, line.commit_summary))
        for mutant in site.mutants:
            evidence_parts.extend(
                (
                    mutant.qualified_function_name,
                    mutant.mutation.original_segment,
                    mutant.mutation.mutated_segment,
                    mutant.evidence.adversarial_test.targeted_behavior,
                    mutant.evidence.failing_assertion.message,
                )
            )
    evidence_tokens = _tokens(" ".join(evidence_parts))
    best_claim = None
    best_overlap: set[str] = set()
    for commit, summary in summaries:
        overlap = _tokens(summary).intersection(evidence_tokens)
        if _COMMIT_CLAIM_RE.search(summary) and len(overlap) > len(best_overlap):
            best_claim = (commit, summary)
            best_overlap = overlap
    signals = []
    reason = None
    if best_claim is not None and best_overlap:
        signals.extend(("commit_claim", "commit_evidence_overlap"))
        commit, summary = best_claim
        reason = (
            f"Commit {commit[:7]} says “{summary},” but execution shows the "
            "submitted tests did not protect that claimed behavior."
        )
    if len(site_results) > 1:
        signals.append("multiple_unverified_sites")
    mutant_count = sum(site.survivor_count for site in site_results)
    if mutant_count > 1:
        signals.append("multiple_surviving_mutations")
    score = (
        int(best_claim is not None and bool(best_overlap)),
        len(best_overlap),
        len(site_results),
        mutant_count,
    )
    return score, tuple(signals), reason


def _ranked_function_groups(probe: ProbeSummary) -> tuple[ReportFunctionGroup, ...]:
    grouped = defaultdict(list)
    for site in probe.results:
        if not site.mutants:
            continue
        grouped[(site.grounding.path, site.mutants[0].qualified_function_name)].append(
            site
        )
    ranked = []
    for (path, function_name), sites in grouped.items():
        score, signals, reason = _group_ranking(sites)
        ranked.append(
            (
                score,
                ReportFunctionGroup(
                    path=path,
                    qualified_function_name=function_name,
                    site_ids=tuple(site.site_id for site in sites),
                    site_count=len(sites),
                    mutant_count=sum(site.survivor_count for site in sites),
                    ranking_signals=signals,
                    priority_reason=reason,
                ),
            )
        )
    return tuple(
        group
        for _, group in sorted(
            ranked,
            key=lambda item: (
                *(-value for value in item[0]),
                item[1].path,
                item[1].qualified_function_name,
            ),
        )
    )


def _rate(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.3f}"


def _prose(value: object) -> str:
    """Keep readable prose literal while removing carriage-return artifacts."""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def _code_span(value: object) -> str:
    text = _prose(value).replace("\n", " ")
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    delimiter = "`" * max(1, longest + 1)
    padding = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{delimiter}{padding}{text}{padding}{delimiter}"


def _source_block(authored_lines) -> str:
    source = "\n".join(
        f"{line.line:>4} | {line.text}" for line in authored_lines
    )
    longest = max((len(run) for run in re.findall(r"`+", source)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}python\n{source}\n{fence}"


def render_report_markdown(report: FencepostReport) -> str:
    subject = report.student_name or report.student_email
    coverage = report.authored_line_coverage
    tests = (
        f"{report.submitted_suite_tests_passed} tests"
        if report.submitted_suite_tests_passed is not None
        else "submitted tests"
    )
    lines = [
        "# Fencepost comprehension report",
        "",
        _prose(report.formative_notice),
        "",
        "## Summary",
        "",
    ]
    if not coverage.sufficient_for_assessment:
        lines.extend(
            [
                (
                    f"{_prose(subject)}'s {tests} pass, but they execute "
                    f"{coverage.covered_authored_mutatable_line_count} of "
                    f"{coverage.authored_mutatable_line_count} mutatable lines they "
                    "wrote. Fencepost cannot assess understanding of code their tests "
                    "never run."
                ),
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"{_prose(subject)}'s {tests} pass.",
                "",
                (
                    f"We made {report.mutation_summary.total_mutants} small changes "
                    "to code they wrote; their tests caught "
                    f"{report.mutation_summary.killed_by_submitted_tests}. Of the "
                    f"{report.mutation_summary.survived_submitted_tests} changes they "
                    f"missed, {report.question_mutant_count} are fair to discuss. "
                    f"We withheld {report.not_questioned_mutant_count} that would not "
                    "make a fair question."
                ),
                "",
            ]
        )
    rate = (
        "unavailable" if coverage.rate is None else f"{coverage.rate:.0%}"
    )
    lines.extend(
        [
            (
                "Authored-line coverage: "
                f"**{coverage.covered_authored_mutatable_line_count} of "
                f"{coverage.authored_mutatable_line_count} ({rate})**. The minimum "
                f"for an assessable zero-finding report is {coverage.minimum_rate:.0%}."
            ),
            "",
            f"Analyzed repository commit: {_code_span(report.repository_commit)}.",
            "",
            "## What their tests already protect",
            "",
        ]
    )
    for function in report.function_assessments:
        if function.status == "CLEAN":
            description = (
                f"all {function.killed_by_submitted_tests} of "
                f"{function.total_mutants} changes caught"
            )
        elif function.status == "GAPS_FOUND":
            description = (
                f"{function.contract_real_gap_mutants} verified behavior changes "
                f"among {function.total_mutants} changes; "
                f"{function.question_site_count} fair question site(s)"
            )
        else:
            description = function.status.lower().replace("_", " ")
        lines.append(
            f"- {_code_span(function.qualified_function_name)} — {description}."
        )
    lines.extend(["", "## Deliberately not asked", ""])
    if not report.deliberately_not_asked and not report.pedagogically_not_asked:
        lines.extend(["No changes were withheld from student questions.", ""])
    for item in report.deliberately_not_asked:
        lines.extend(
            [
                f"### {item.path}:{item.line}",
                "",
                _prose(item.plain_language_reason),
                "",
                f"{_code_span(item.original_segment)} -> {_code_span(item.mutated_segment)}",
                "",
                "<details><summary>Technical evidence for audit</summary>",
                "",
                "```python",
                item.strict_test.source,
                "```",
                "",
                f"{_code_span(item.strict_failure_evidence.nodeid)}: {_prose(item.strict_failure_evidence.message)}",
                "",
                "</details>",
                "",
            ]
        )
    for item in report.pedagogically_not_asked:
        mutant = item.mutant
        lines.extend(
            [
                f"### {mutant.mutant.candidate.path}:{mutant.mutant.candidate.anchor.line}",
                "",
                "This execution witness was withheld because it would make a poor CS2 question.",
                "",
                *(_prose(reason) for reason in item.reasons),
                "",
                f"{_code_span(mutant.mutation.original_segment)} -> {_code_span(mutant.mutation.mutated_segment)}",
                "",
            ]
        )

    lines.extend(["## Conversations worth having", ""])
    places = {site.site_id: site for site in report.places}
    for group in report.function_groups:
        lines.extend(
            [
                f"### {_code_span(group.qualified_function_name)}",
                "",
                (
                    f"{group.site_count} source site(s); "
                    f"{group.mutant_count} surviving change(s)."
                ),
                "",
            ]
        )
        if group.priority_reason:
            lines.extend([f"**Why this comes first.** {_prose(group.priority_reason)}", ""])
        for site_id in group.site_ids:
            site = places[site_id]
            attribution = "; ".join(
                f"line {line.line}, commit {line.commit[:7]} on {line.author_date} "
                f"({line.commit_summary})"
                for line in site.grounding.authored_lines
            )
            lines.extend(
                [
                    f"#### {site.grounding.path}:{site.grounding.start_line}",
                    "",
                    attribution + ".",
                    "",
                    _source_block(site.grounding.authored_lines),
                    "",
                ]
            )
            if site.question is not None:
                lines.extend(["**Question:** " + _prose(site.question.question_text), ""])
            for mutant in site.mutants:
                failure = mutant.evidence.failing_assertion
                submitted_tests = (
                    f"{mutant.submitted_suite_tests_passed} tests"
                    if mutant.submitted_suite_tests_passed is not None
                    else "submitted tests"
                )
                lines.extend(
                    [
                        f"- {_code_span(mutant.mutation.original_segment)} -> {_code_span(mutant.mutation.mutated_segment)}",
                        "",
                        f"  Their {submitted_tests} passed; the adversarial test failed at {_code_span(failure.nodeid)}: {_prose(failure.message)}",
                        "",
                        "  <details><summary>Full source diff</summary>",
                        "",
                        "  ```diff",
                        mutant.mutation.unified_diff,
                        "  ```",
                        "",
                        "  </details>",
                        "",
                    ]
                )
            if site.answer is not None:
                lines.extend(["Student answer:", "", _prose(site.answer), ""])
            if site.assessment is not None:
                lines.extend(
                    [
                        f"Formative assessment: **{site.assessment.verdict}**",
                        "",
                        _prose(site.assessment.feedback),
                        "",
                        "Execution evidence cited:",
                        "",
                    ]
                )
                for citation in site.assessment.citations:
                    lines.append(
                        f"- {_code_span(citation.nodeid)} — {_prose(citation.message)} ({_code_span(citation.artifact_ref)})"
                    )
                lines.append("")

    lines.extend(
        [
            "## Method: equivalence triage",
            "",
            (
                f"STRICT equivalent rate: **{_rate(report.equivalent_rate_strict)}** "
                f"({report.probable_equivalent_count_strict} probable equivalent, "
                f"{report.real_gap_count_strict} real gap, "
                f"{report.unresolved_count_strict} unresolved)."
            ),
            "",
            (
                f"CONTRACT equivalent rate: **{_rate(report.equivalent_rate_contract)}** "
                f"({report.probable_equivalent_count_contract} probable equivalent, "
                f"{report.real_gap_count_contract} real gap, "
                f"{report.unresolved_count_contract} unresolved)."
            ),
            "",
            "CONTRACT limitation: " + _prose(report.contract_limitation),
            "",
            "## Traceability",
            "",
            "Every behavioral statement above points to an execution artifact. Core artifacts:",
            "",
        ]
    )
    lines.extend(f"- {_code_span(path)}" for path in report.traceability_artifacts)
    lines.append("")
    return "\n".join(lines)
