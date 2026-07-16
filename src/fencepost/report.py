"""Stage 7: stable execution-traceable report artifacts for instructors and UIs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Sequence

from .models import (
    ContractShieldedReportItem,
    FencepostReport,
    ProbeSummary,
    TriageSummary,
    json_value,
)
from .probe import source_span_segment
from .triage import SurvivorContext


REPORT_SCHEMA_VERSION = "2.0"


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
                strict_test=item.strict_winning_test,
                strict_failure_evidence=item.strict_failure_evidence,
                artifact_refs=(
                    f"triage/strict/{candidate_id}/attempt-{attempt:02d}/attempt.json",
                    f"triage/contract/{candidate_id}/result.json",
                ),
            )
        )

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
        baseline_artifact_ref="baseline/result.json",
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
    lines = [
        "# Fencepost comprehension report",
        "",
        _prose(report.formative_notice),
        "",
        "## Summary",
        "",
        (
            f"{_prose(subject)}'s submitted pytest suite passed. "
            f"Fencepost found {report.unverified_place_count} execution-grounded "
            "source sites where understanding remains unverified."
        ),
        "",
        f"Analyzed repository commit: {_code_span(report.repository_commit)}.",
        "",
        "## Places to discuss",
        "",
    ]
    if not report.places:
        lines.extend(["No CONTRACT-mode real-gap sites were available for questions.", ""])

    for index, site in enumerate(report.places, start=1):
        attribution = "; ".join(
            f"line {line.line}, commit {line.commit[:7]} on {line.author_date} "
            f"({line.commit_summary})"
            for line in site.grounding.authored_lines
        )
        lines.extend(
            [
                f"### {index}. {site.grounding.path}:{site.grounding.start_line}",
                "",
                attribution + ".",
                "",
                "Authored source:",
                "",
                _source_block(site.grounding.authored_lines),
                "",
            ]
        )
        if site.question is not None:
            lines.extend(["Question:", "", _prose(site.question.question_text), ""])
        else:
            lines.extend(["Question generation did not complete for this site.", ""])

        lines.extend(
            [
                (
                    f"Supporting execution evidence ({site.survivor_count} surviving "
                    f"mutation{'s' if site.survivor_count != 1 else ''}):"
                ),
                "",
            ]
        )
        for evidence_index, mutant in enumerate(site.mutants, start=1):
            failure = mutant.evidence.failing_assertion
            lines.extend(
                [
                    (
                        f"{evidence_index}. {_code_span(mutant.mutation.original_segment)} "
                        f"-> {_code_span(mutant.mutation.mutated_segment)}"
                    ),
                    "",
                    (
                        "   Original passed; mutant failed at "
                        f"{_code_span(failure.nodeid)}: {_prose(failure.message)}"
                    ),
                    "",
                    f"   Artifact: {_code_span(mutant.evidence.triage_artifact_ref)}.",
                    "",
                ]
            )

        if site.answer is None:
            lines.extend(["No student answer was supplied in this run.", ""])
        else:
            lines.extend(["Student answer:", "", _prose(site.answer), ""])
            if site.assessment is not None:
                lines.extend(
                    [
                        f"Formative assessment: **{site.assessment.verdict}**",
                        "",
                        _prose(site.assessment.feedback),
                        "",
                        "Evidence cited:",
                        "",
                    ]
                )
                for citation in site.assessment.citations:
                    lines.append(
                        f"- {_code_span(citation.nodeid)} -- {_prose(citation.message)} "
                        f"({_code_span(citation.artifact_ref)})"
                    )
                lines.append("")
            else:
                lines.extend(["The submitted answer could not be assessed in this run.", ""])

    lines.extend(["## Deliberately not asked", ""])
    if not report.deliberately_not_asked:
        lines.extend(["No strict-only, contract-shielded mutants were found.", ""])
    for item in report.deliberately_not_asked:
        lines.extend(
            [
                f"### {item.path}:{item.line}",
                "",
                (
                    f"{_code_span(item.original_segment)} -> "
                    f"{_code_span(item.mutated_segment)}"
                ),
                "",
                _prose(item.reason),
                "",
                (
                    "STRICT evidence retained: "
                    f"{_code_span(item.strict_failure_evidence.nodeid)} -- "
                    f"{_prose(item.strict_failure_evidence.message)}."
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## Equivalence triage",
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
