"""Stages 1-4 orchestration: attribute, select, mutate, execute."""

from __future__ import annotations

import json
import os
import statistics
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

from .contract import CONTRACT_LIMITATION, CONTRACT_RULES
from .models import (
    AnalysisResult,
    AuthoredLineCoverage,
    BlameLine,
    ExecutionResult,
    MutantResult,
    MutationCandidate,
    RunConfig,
    TriageConfig,
    json_value,
    pytest_pass_count,
)
from .mutation import (
    GeneratedMutation,
    MutationError,
    enumerate_candidates,
    generate_mutation,
)
from .repository import (
    RepositoryError,
    SourceFile,
    blame_file,
    extract_archive,
    load_source_files,
    resolve_commit,
)
from .probe import run_probes
from .report import build_report
from .sandbox import DockerSandbox, SandboxError
from .triage import (
    build_survivor_context,
    candidate_function_name,
    triage_survivors,
)

if TYPE_CHECKING:
    from .adversarial import AdversarialTestGenerator
    from .probe import ComprehensionProbeAgent


class PipelineError(RuntimeError):
    pass


MIN_AUTHORED_LINE_COVERAGE = 0.50


@dataclass(frozen=True)
class _EligibleCandidate:
    candidate: MutationCandidate
    source: SourceFile


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_value(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _summary_payload(result: AnalysisResult) -> dict[str, object]:
    payload = json_value(result)
    triage = result.triage
    cost_note = (
        "STRICT and CONTRACT each generate tests independently, and every generation "
        "is a separate model call. A full two-mode run can take several minutes and "
        "consume the configured provider's usage allowance; "
        "use triage_attempts and max_survivors to bound a demonstration run."
    )
    if triage is None:
        survivors = sum(
            mutant.execution.status == "survived"
            for mutant in result.mutant_results
        )
        payload.update(
            {
                "total_survivors": survivors,
                "real_gap_count_strict": 0,
                "probable_equivalent_count_strict": 0,
                "unresolved_count_strict": survivors,
                "equivalent_rate_strict": None,
                "real_gap_count_contract": 0,
                "probable_equivalent_count_contract": 0,
                "unresolved_count_contract": survivors,
                "equivalent_rate_contract": None,
                "invalid_contract_attempts": 0,
                "triage_complete": False,
                "selected_survivor_count": 0,
                "generator_call_count": 0,
                "generator_wall_clock_seconds": 0.0,
                "triage_wall_clock_seconds": 0.0,
                "contract_shielded": [],
                "probe_target_mutant_ids": [],
                "contract_rules": json_value(CONTRACT_RULES),
                "contract_limitation": CONTRACT_LIMITATION,
                "triage_cost_note": cost_note,
            }
        )
    else:
        payload.update(
            {
                "total_survivors": triage.total_survivors,
                "real_gap_count_strict": triage.real_gap_count_strict,
                "probable_equivalent_count_strict": triage.probable_equivalent_count_strict,
                "unresolved_count_strict": triage.unresolved_count_strict,
                "equivalent_rate_strict": triage.equivalent_rate_strict,
                "real_gap_count_contract": triage.real_gap_count_contract,
                "probable_equivalent_count_contract": triage.probable_equivalent_count_contract,
                "unresolved_count_contract": triage.unresolved_count_contract,
                "equivalent_rate_contract": triage.equivalent_rate_contract,
                "invalid_contract_attempts": triage.invalid_contract_attempts,
                "triage_complete": triage.triage_complete,
                "selected_survivor_count": triage.selected_survivor_count,
                "generator_call_count": triage.generator_call_count,
                "generator_wall_clock_seconds": triage.generator_wall_clock_seconds,
                "triage_wall_clock_seconds": triage.triage_wall_clock_seconds,
                "contract_shielded": triage.contract_shielded,
                "probe_target_mutant_ids": triage.probe_target_mutant_ids,
                "contract_rules": triage.contract_rules,
                "contract_limitation": triage.contract_limitation,
                "triage_cost_note": cost_note,
            }
        )
    return payload


def _blame_index(
    repo: Path, commit: str, sources: tuple[SourceFile, ...], student_email: str
) -> dict[str, dict[int, BlameLine]]:
    return {
        source.path: {
            line.line: line
            for line in blame_file(repo, commit, source.path, student_email)
        }
        for source in sources
    }


def _student_name(blame: dict[str, dict[int, BlameLine]]) -> str | None:
    names = Counter(
        line.author_name
        for file_lines in blame.values()
        for line in file_lines.values()
        if line.is_student and line.author_name
    )
    return names.most_common(1)[0][0] if names else None


def _candidate_inventory(
    sources: tuple[SourceFile, ...],
    blame: dict[str, dict[int, BlameLine]],
    covered_lines: dict[str, tuple[int, ...]],
) -> tuple[
    tuple[_EligibleCandidate, ...],
    AuthoredLineCoverage,
    dict[str, str],
]:
    eligible: list[_EligibleCandidate] = []
    authored_mutatable_lines: set[tuple[str, int]] = set()
    covered_authored_mutatable_lines: set[tuple[str, int]] = set()
    function_by_candidate: dict[str, str] = {}
    for source in sources:
        covered = set(covered_lines.get(source.path, ()))
        attributed = blame[source.path]
        try:
            candidates = enumerate_candidates(source.text, source.path)
        except SyntaxError as exc:
            raise PipelineError(f"cannot parse {source.path}: {exc}") from exc
        for candidate in candidates:
            line = attributed.get(candidate.anchor.line)
            if line is None or not line.is_student:
                continue
            key = (source.path, candidate.anchor.line)
            authored_mutatable_lines.add(key)
            if candidate.anchor.line not in covered:
                continue
            covered_authored_mutatable_lines.add(key)
            eligible.append(_EligibleCandidate(candidate=candidate, source=source))
            function_by_candidate[candidate.id] = candidate_function_name(
                source.text, candidate
            )
    total = len(authored_mutatable_lines)
    covered_count = len(covered_authored_mutatable_lines)
    rate = covered_count / total if total else None
    coverage = AuthoredLineCoverage(
        authored_mutatable_line_count=total,
        covered_authored_mutatable_line_count=covered_count,
        rate=rate,
        minimum_rate=MIN_AUTHORED_LINE_COVERAGE,
        sufficient_for_assessment=(
            rate is not None and rate >= MIN_AUTHORED_LINE_COVERAGE
        ),
        artifact_ref="selection.json",
    )
    return tuple(eligible), coverage, function_by_candidate


def _mutant_timeout(config: RunConfig, baseline_duration: float) -> float:
    return min(
        config.mutant_timeout_cap_seconds,
        max(5.0, (4.0 * baseline_duration) + 2.0),
    )


def _mutant_workers(config: RunConfig) -> int:
    cpu_limit = max(1, (os.cpu_count() or 2) - 1)
    if config.mutant_workers is None:
        return min(4, cpu_limit)
    if config.mutant_workers < 1:
        raise PipelineError("mutant worker count must be at least 1")
    return min(config.mutant_workers, cpu_limit)


def _broken_generation(candidate: MutationCandidate, error: Exception) -> MutantResult:
    from .models import SourceSpan

    return MutantResult(
        candidate=candidate,
        generated_anchor=SourceSpan(0, 0, 0, 0),
        execution=ExecutionResult(
            status="broken",
            exit_code=None,
            duration_seconds=0.0,
            stdout="",
            stderr=f"mutant generation failed: {error}",
        ),
    )


def _raise_if_initial_mutants_all_broken(
    artifact_dir: Path, results: list[MutantResult], candidate_count: int
) -> None:
    """Stop a uniformly broken run before it executes the remaining batch."""
    probe_size = min(5, candidate_count)
    if len(results) != probe_size or not all(
        result.execution.status == "broken" for result in results
    ):
        return
    _write_json(
        artifact_dir / "all-broken.json",
        {
            "error": f"The first {probe_size} eligible mutants were all broken.",
            "diagnostic": (
                "Broken mutants indicate an invalid operator or execution harness, "
                "not a student comprehension finding. The run was stopped before "
                "executing every candidate."
            ),
            "attempted_mutants": probe_size,
            "eligible_mutants": candidate_count,
            "median_mutant_seconds": statistics.median(
                result.execution.duration_seconds for result in results
            ),
        },
    )
    raise PipelineError(
        f"the first {probe_size} eligible mutants were all broken; "
        "inspect all-broken.json because the mutation operator or sandbox harness is wrong"
    )


def run_analysis(
    config: RunConfig,
    *,
    adversarial_generator: "AdversarialTestGenerator | None" = None,
    triage_config: TriageConfig | None = None,
    probe_agent: "ComprehensionProbeAgent | None" = None,
    probe_answers: Mapping[str, str] | None = None,
) -> AnalysisResult:
    """Run stages 1-4 and optionally Stages 5-7 triage, probe, and report.

    The submitted pytest suite is run exactly as submitted.  Blame only filters
    the source lines eligible to mutate; it does not filter tests by authorship.

    Deliberate first-build limitation: projects requiring student-controlled
    dependency installation (for example ``requirements.txt``) are unsupported.
    The sandbox contains only the Python standard library, pytest, and coverage.
    """
    started = time.monotonic()
    run_started_at = datetime.now(timezone.utc).isoformat()
    if triage_config is not None and adversarial_generator is None:
        raise PipelineError("triage configuration requires an adversarial generator")
    if adversarial_generator is not None and triage_config is None:
        triage_config = TriageConfig()
    if probe_agent is not None and adversarial_generator is None:
        raise PipelineError("probe generation requires equivalence triage")
    if probe_answers and probe_agent is None:
        raise PipelineError("probe answers require a configured probe agent")
    repo = config.repo.resolve()
    artifact_dir = config.artifact_dir.resolve()
    if artifact_dir.exists():
        if any(artifact_dir.iterdir()):
            raise PipelineError(f"artifact directory must be empty: {artifact_dir}")
    else:
        artifact_dir.mkdir(parents=True)

    try:
        commit = resolve_commit(repo, config.commit)
        sources = load_source_files(repo, commit)
        blame = _blame_index(repo, commit, sources, config.student_email)
    except RepositoryError as exc:
        raise PipelineError(str(exc)) from exc

    workers = _mutant_workers(config)
    _write_json(
        artifact_dir / "run.json",
        {
            "commit": commit,
            "repository_path": str(repo),
            "run_started_at": run_started_at,
            "student_email": config.student_email,
            "image": config.image,
            "mutant_workers": workers,
            "triage": {
                "enabled": adversarial_generator is not None,
                "generator": type(adversarial_generator).__name__
                if adversarial_generator is not None
                else None,
                "model": getattr(adversarial_generator, "model", None),
                "config": triage_config,
                "modes": {
                    "STRICT": "unrestricted Python distinguishability",
                    "CONTRACT": "statically validated plain-caller domain",
                },
                "contract_rules": CONTRACT_RULES,
                "contract_limitation": CONTRACT_LIMITATION,
            },
            "probe": {
                "enabled": probe_agent is not None,
                "agent": type(probe_agent).__name__ if probe_agent is not None else None,
                "model": getattr(probe_agent, "model", None),
                "submitted_answer_count": len(probe_answers or {}),
                "target_policy": "CONTRACT-mode REAL_GAP only",
            },
            "scope": {
                "supported": (
                    "Committed Python projects whose tests use only the standard library and pytest; "
                    "repository-root, conventional src/, and direct __init__.py package roots are importable."
                ),
                "unsupported": (
                    "Installing student-controlled dependencies or package metadata such as requirements.txt, "
                    "pyproject dependencies, setup.py, and custom build/import layouts outside detected roots."
                ),
            },
            "sources": [
                {"path": source.path, "sha256": source.sha256}
                for source in sources
            ],
            "blame": blame,
        },
    )

    sandbox = DockerSandbox(config.image, _project_root(), config.build_image)
    try:
        sandbox.ensure_image()
    except SandboxError as exc:
        raise PipelineError(str(exc)) from exc

    with tempfile.TemporaryDirectory(prefix="fencepost-") as temporary:
        temp_root = Path(temporary)
        baseline_tree = temp_root / "baseline-tree"
        try:
            extract_archive(repo, commit, baseline_tree)
            baseline = sandbox.baseline(
                baseline_tree,
                artifact_dir / "baseline",
                config.baseline_timeout_seconds,
            )
            _write_json(artifact_dir / "baseline" / "result.json", baseline.execution)
        except (RepositoryError, SandboxError) as exc:
            raise PipelineError(str(exc)) from exc

        covered = {
            path: lines
            for path, lines in baseline.covered_lines.items()
            if path in {source.path for source in sources}
        }
        try:
            sandbox.preflight(
                baseline_tree,
                artifact_dir / "preflight",
                _mutant_timeout(config, baseline.execution.duration_seconds),
            )
        except SandboxError as exc:
            raise PipelineError(str(exc)) from exc
        eligible, authored_line_coverage, function_by_candidate = (
            _candidate_inventory(sources, blame, covered)
        )
        _write_json(
            artifact_dir / "selection.json",
            {
                "covered_lines": covered,
                "authored_line_coverage": authored_line_coverage,
                "eligible_candidates": [item.candidate for item in eligible],
                "candidate_functions": function_by_candidate,
            },
        )

        timeout = _mutant_timeout(config, baseline.execution.duration_seconds)
        batch_input = temp_root / "batch-input"
        batch_sources = batch_input / "sources"
        batch_sources.mkdir(parents=True)
        prepared: dict[str, tuple[_EligibleCandidate, GeneratedMutation]] = {}
        generation_failures: dict[str, MutantResult] = {}
        batch_manifest: list[dict[str, str]] = []

        for item in eligible:
            candidate = item.candidate
            mutant_dir = artifact_dir / "mutants" / candidate.id
            mutant_dir.mkdir(parents=True, exist_ok=True)
            try:
                generated = generate_mutation(item.source.text, candidate)
            except (MutationError, SyntaxError, ValueError) as exc:
                result = _broken_generation(candidate, exc)
                generation_failures[candidate.id] = result
                _write_json(mutant_dir / "result.json", result)
                continue

            source_file = f"{candidate.id}.py"
            (batch_sources / source_file).write_text(generated.source, encoding="utf-8")
            (mutant_dir / "mutated.py").write_text(generated.source, encoding="utf-8")
            (mutant_dir / "original.py").write_text(item.source.text, encoding="utf-8")
            prepared[candidate.id] = (item, generated)
            batch_manifest.append(
                {
                    "id": candidate.id,
                    "path": candidate.path,
                    "source_file": source_file,
                }
            )

        _write_json(
            batch_input / "manifest.json",
            {
                "workers": workers,
                "timeout_seconds": timeout,
                "import_roots": sandbox.import_roots(baseline_tree),
                "mutants": batch_manifest,
            },
        )
        if batch_manifest:
            try:
                batch_run = sandbox.batch(
                    baseline_tree,
                    batch_input,
                    artifact_dir / "batch",
                    mutant_count=len(batch_manifest),
                    per_mutant_timeout=timeout,
                    workers=workers,
                )
            except SandboxError as exc:
                raise PipelineError(str(exc)) from exc
            batch_executions = batch_run.results
            batch_duration = batch_run.container_duration_seconds
        else:
            batch_executions = {}
            batch_duration = 0.0

        mutant_results: list[MutantResult] = []
        for item in eligible:
            candidate = item.candidate
            if candidate.id in generation_failures:
                result = generation_failures[candidate.id]
            elif candidate.id in batch_executions:
                _, generated = prepared[candidate.id]
                result = MutantResult(
                    candidate=candidate,
                    generated_anchor=generated.generated_anchor,
                    execution=batch_executions[candidate.id],
                )
                _write_json(
                    artifact_dir / "mutants" / candidate.id / "result.json", result
                )
            elif batch_manifest and batch_run.aborted_all_broken:
                break
            else:
                raise PipelineError(
                    f"batch result is missing eligible mutant {candidate.id}"
                )
            mutant_results.append(result)
            _raise_if_initial_mutants_all_broken(
                artifact_dir, mutant_results, len(eligible)
            )

        if batch_manifest and batch_run.aborted_all_broken:
            raise PipelineError(
                "mutant batch aborted after uniformly broken initial results; "
                "inspect batch/batch-results.json"
            )

        triage_summary = None
        probe_summary = None
        report_summary = None
        survivor_contexts = []
        if adversarial_generator is not None and triage_config is not None:
            import_roots = sandbox.import_roots(baseline_tree)
            for mutant in mutant_results:
                if mutant.execution.status != "survived":
                    continue
                prepared_item = prepared.get(mutant.candidate.id)
                if prepared_item is None:
                    raise PipelineError(
                        f"surviving mutant {mutant.candidate.id} has no generated source"
                    )
                eligible_item, generated = prepared_item
                try:
                    context = build_survivor_context(
                        mutant,
                        original_source=eligible_item.source.text,
                        mutated_source=generated.source,
                        import_roots=import_roots,
                    )
                except (SyntaxError, ValueError) as exc:
                    raise PipelineError(
                        f"cannot build triage context for {mutant.candidate.id}: {exc}"
                    ) from exc
                survivor_contexts.append(context)
            triage_summary = triage_survivors(
                survivor_contexts,
                generator=adversarial_generator,
                sandbox=sandbox,
                baseline_tree=baseline_tree,
                artifact_dir=artifact_dir,
                config=triage_config,
                workers=workers,
            )
            if probe_agent is not None:
                probe_summary = run_probes(
                    triage_summary,
                    survivor_contexts,
                    blame=blame,
                    agent=probe_agent,
                    answers=probe_answers,
                    artifact_dir=artifact_dir,
                )

        if triage_summary is not None and probe_summary is not None:
            report_summary = build_report(
                commit=commit,
                student_email=config.student_email,
                student_name=_student_name(blame),
                triage=triage_summary,
                probe=probe_summary,
                contexts=survivor_contexts,
                submitted_suite_tests_passed=pytest_pass_count(
                    baseline.execution.stdout
                ),
                authored_line_coverage=authored_line_coverage,
                mutant_results=mutant_results,
                function_by_mutant_id=function_by_candidate,
                artifact_dir=artifact_dir,
                repository_path=str(repo),
                run_started_at=run_started_at,
            )

    result = AnalysisResult(
        repo=repo,
        commit=commit,
        baseline_duration_seconds=baseline.execution.duration_seconds,
        covered_lines=covered,
        mutant_results=tuple(mutant_results),
        mutant_workers=workers,
        batch_duration_seconds=batch_duration,
        elapsed_seconds=time.monotonic() - started,
        artifact_dir=artifact_dir,
        triage=triage_summary,
        probe=probe_summary,
        report=report_summary,
    )
    _write_json(artifact_dir / "summary.json", _summary_payload(result))
    if result.mutant_count and all(
        mutant.execution.status == "broken" for mutant in result.mutant_results
    ):
        _write_json(
            artifact_dir / "all-broken.json",
            {
                "error": "Every eligible mutant was broken.",
                "diagnostic": (
                    "Broken mutants indicate an invalid operator or execution harness, "
                    "not a student comprehension finding."
                ),
                "mutant_count": result.mutant_count,
                "median_mutant_seconds": statistics.median(
                    mutant.execution.duration_seconds for mutant in result.mutant_results
                ),
            },
        )
        raise PipelineError(
            f"all {result.mutant_count} eligible mutants were broken; "
            "inspect all-broken.json because the mutation operator or sandbox harness is wrong"
        )
    return result
