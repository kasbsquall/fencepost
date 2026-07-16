"""Stage 5: execution-grounded equivalence triage for surviving mutants."""

from __future__ import annotations

import ast
import difflib
import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Sequence

from .adversarial import (
    AdversarialGeneratorError,
    AdversarialTestGenerator,
)
from .models import (
    AdversarialAttempt,
    AdversarialExecution,
    AdversarialTestRequest,
    AttemptFeedback,
    GeneratedAdversarialTest,
    MutantResult,
    SurvivorTriageResult,
    TriageConfig,
    TriageJob,
    TriageJobResult,
    TriageSummary,
    json_value,
)
from .sandbox import DockerSandbox, SandboxError


@dataclass(frozen=True)
class SurvivorContext:
    mutant: MutantResult
    original_source: str
    mutated_source: str
    module_path: str
    qualified_function_name: str
    original_function: str
    mutated_function: str
    unified_diff: str


@dataclass
class _SurvivorState:
    context: SurvivorContext
    attempts: list[AdversarialAttempt] = field(default_factory=list)
    feedback: list[AttemptFeedback] = field(default_factory=list)
    generation_attempts: int = 0
    valid_attempts: int = 0
    invalid_attempts: int = 0
    consecutive_invalid_attempts: int = 0
    terminal: SurvivorTriageResult | None = None


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_value(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _nodes_along_path(source: str, mutant: MutantResult) -> list[ast.AST]:
    node: ast.AST = ast.parse(source, filename=mutant.candidate.path)
    nodes = [node]
    for step in mutant.candidate.ast_path:
        value = getattr(node, step.field)
        node = value if step.index is None else value[step.index]
        if not isinstance(node, ast.AST):
            raise ValueError(
                f"mutation path for {mutant.candidate.id} resolves through a non-AST value"
            )
        nodes.append(node)
    return nodes


def _function_context(
    source: str, mutant: MutantResult
) -> tuple[str, str]:
    nodes = _nodes_along_path(source, mutant)
    function = next(
        (
            node
            for node in reversed(nodes)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ),
        None,
    )
    if function is None:
        raise ValueError(
            f"mutation {mutant.candidate.id} is not enclosed by a function"
        )
    names = [
        node.name
        for node in nodes
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and nodes.index(node) <= nodes.index(function)
    ]
    segment = ast.get_source_segment(source, function)
    return ".".join(names), segment if segment is not None else ast.unparse(function)


def _import_module(path: str, import_roots: Sequence[str]) -> str:
    relative = PurePosixPath(path)
    matching = [
        PurePosixPath(root)
        for root in import_roots
        if root != "."
        and tuple(relative.parts[: len(PurePosixPath(root).parts)])
        == PurePosixPath(root).parts
    ]
    if matching:
        root = max(matching, key=lambda item: len(item.parts))
        relative = PurePosixPath(*relative.parts[len(root.parts) :])
    parts = list(relative.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    if not parts:
        raise ValueError(f"cannot derive an import module from {path!r}")
    return ".".join(parts)


def build_survivor_context(
    mutant: MutantResult,
    *,
    original_source: str,
    mutated_source: str,
    import_roots: Sequence[str],
) -> SurvivorContext:
    original_name, original_function = _function_context(original_source, mutant)
    mutated_name, mutated_function = _function_context(mutated_source, mutant)
    if original_name != mutated_name:
        raise ValueError(
            f"mutation {mutant.candidate.id} changed its enclosing function identity"
        )
    diff = "\n".join(
        difflib.unified_diff(
            original_function.splitlines(),
            mutated_function.splitlines(),
            fromfile="original",
            tofile="mutant",
            lineterm="",
        )
    )
    return SurvivorContext(
        mutant=mutant,
        original_source=original_source,
        mutated_source=mutated_source,
        module_path=_import_module(mutant.candidate.path, import_roots),
        qualified_function_name=original_name,
        original_function=original_function,
        mutated_function=mutated_function,
        unified_diff=diff,
    )


def _execution_summary(execution: AdversarialExecution | None) -> str | None:
    if execution is None:
        return None
    detail = execution.failure.message if execution.failure is not None else ""
    return (
        f"status={execution.status} exit={execution.exit_code} "
        f"tests={execution.tests_collected} skipped={execution.tests_skipped} {detail}"
    ).strip()


def _terminal_result(
    state: _SurvivorState,
    label: str,
    *,
    winning_test: GeneratedAdversarialTest | None = None,
    unresolved_reason: str | None = None,
) -> SurvivorTriageResult:
    failure = None
    if label == "REAL_GAP" and state.attempts:
        mutant_execution = state.attempts[-1].mutant
        if mutant_execution is not None:
            failure = mutant_execution.failure
    return SurvivorTriageResult(
        mutant=state.context.mutant,
        label=label,
        attempts=tuple(state.attempts),
        attempts_used=state.generation_attempts,
        valid_attempts=state.valid_attempts,
        invalid_attempts=state.invalid_attempts,
        winning_test=winning_test,
        failure_evidence=failure,
        unresolved_reason=unresolved_reason,
    )


def _persist_context(artifact_dir: Path, context: SurvivorContext) -> None:
    _write_json(
        artifact_dir / "triage" / context.mutant.candidate.id / "context.json",
        {
            "mutant": context.mutant,
            "module_path": context.module_path,
            "qualified_function_name": context.qualified_function_name,
            "original_function": context.original_function,
            "mutated_function": context.mutated_function,
            "unified_diff": context.unified_diff,
        },
    )


def _persist_attempt(
    artifact_dir: Path,
    state: _SurvivorState,
    attempt: AdversarialAttempt,
) -> None:
    attempt_dir = (
        artifact_dir
        / "triage"
        / state.context.mutant.candidate.id
        / f"attempt-{attempt.attempt:02d}"
    )
    attempt_dir.mkdir(parents=True, exist_ok=True)
    (attempt_dir / "test.py").write_text(
        attempt.generated_test.source, encoding="utf-8"
    )
    _write_json(attempt_dir / "generation.json", attempt.generated_test)
    _write_json(attempt_dir / "original-result.json", attempt.original)
    if attempt.mutant is not None:
        _write_json(attempt_dir / "mutant-result.json", attempt.mutant)
    _write_json(attempt_dir / "attempt.json", attempt)


def _persist_terminal(artifact_dir: Path, result: SurvivorTriageResult) -> None:
    _write_json(
        artifact_dir / "triage" / result.mutant.candidate.id / "result.json",
        result,
    )


def _summary(
    states: Sequence[_SurvivorState], *, triage_complete: bool
) -> TriageSummary:
    results = tuple(state.terminal for state in states if state.terminal is not None)
    real_gaps = sum(result.label == "REAL_GAP" for result in results)
    equivalents = sum(result.label == "PROBABLE_EQUIVALENT" for result in results)
    unresolved = sum(result.label == "UNRESOLVED" for result in results)
    decided = real_gaps + equivalents
    rate = equivalents / decided if triage_complete and decided else None
    return TriageSummary(
        total_survivors=len(states),
        real_gap_count=real_gaps,
        probable_equivalent_count=equivalents,
        unresolved_count=unresolved,
        equivalent_rate=rate,
        triage_complete=triage_complete,
        total_attempts=sum(state.generation_attempts for state in states),
        valid_attempts=sum(state.valid_attempts for state in states),
        invalid_original_attempts=sum(state.invalid_attempts for state in states),
        results=results,
    )


def triage_survivors(
    survivors: Sequence[SurvivorContext],
    *,
    generator: AdversarialTestGenerator,
    sandbox: DockerSandbox,
    baseline_tree: Path,
    artifact_dir: Path,
    config: TriageConfig,
    workers: int,
) -> TriageSummary:
    if config.valid_attempts < 1:
        raise ValueError("valid attempt budget must be at least 1")
    if config.invalid_retry_limit < 1:
        raise ValueError("invalid retry limit must be at least 1")
    if config.test_timeout_seconds <= 0:
        raise ValueError("triage test timeout must be positive")

    states = [_SurvivorState(context=context) for context in survivors]
    for state in states:
        _persist_context(artifact_dir, state.context)
    if not states:
        summary = _summary(states, triage_complete=True)
        _write_json(artifact_dir / "triage" / "summary.json", summary)
        return summary

    import_roots = sandbox.import_roots(baseline_tree)
    session_input = artifact_dir / "triage" / "session-input"
    session_output = artifact_dir / "triage" / "session-output"
    session_input.mkdir(parents=True, exist_ok=True)
    session_output.mkdir(parents=True, exist_ok=True)
    triage_complete = True
    round_id = 0

    try:
        with sandbox.triage_session(
            baseline_tree,
            session_input,
            session_output,
            import_roots=import_roots,
            workers=workers,
            per_test_timeout=config.test_timeout_seconds,
        ) as session:
            while any(state.terminal is None for state in states):
                round_id += 1
                jobs: list[TriageJob] = []
                pending: dict[
                    str, tuple[_SurvivorState, GeneratedAdversarialTest]
                ] = {}
                for state in states:
                    if state.terminal is not None:
                        continue
                    state.generation_attempts += 1
                    request = AdversarialTestRequest(
                        mutant=state.context.mutant,
                        attempt=state.generation_attempts,
                        valid_attempts_completed=state.valid_attempts,
                        module_path=state.context.module_path,
                        qualified_function_name=state.context.qualified_function_name,
                        original_function=state.context.original_function,
                        mutated_function=state.context.mutated_function,
                        unified_diff=state.context.unified_diff,
                        prior_attempts=tuple(state.feedback),
                    )
                    try:
                        generated = generator.generate(request)
                    except AdversarialGeneratorError as exc:
                        state.generation_attempts -= 1
                        state.terminal = _terminal_result(
                            state,
                            "UNRESOLVED",
                            unresolved_reason=str(exc),
                        )
                        _persist_terminal(artifact_dir, state.terminal)
                        continue
                    job_id = (
                        f"{state.context.mutant.candidate.id}"
                        f"-attempt-{state.generation_attempts:02d}"
                    )
                    jobs.append(
                        TriageJob(
                            id=job_id,
                            mutant_path=state.context.mutant.candidate.path,
                            mutant_source=state.context.mutated_source,
                            test_source=generated.source,
                            attempt=state.generation_attempts,
                        )
                    )
                    pending[job_id] = (state, generated)

                if not jobs:
                    continue
                batch = session.run_round(round_id, jobs)
                missing = set(pending).difference(batch)
                if missing:
                    raise SandboxError(
                        "triage session omitted job results: "
                        + ", ".join(sorted(missing))
                    )

                for job_id, (state, generated) in pending.items():
                    result: TriageJobResult = batch[job_id]
                    valid_number = (
                        state.valid_attempts + 1
                        if result.outcome != "INVALID_ON_ORIGINAL"
                        else None
                    )
                    attempt = AdversarialAttempt(
                        attempt=state.generation_attempts,
                        valid_attempt_number=valid_number,
                        generated_test=generated,
                        outcome=result.outcome,
                        original=result.original,
                        mutant=result.mutant,
                    )
                    state.attempts.append(attempt)
                    _persist_attempt(artifact_dir, state, attempt)
                    state.feedback.append(
                        AttemptFeedback(
                            attempt=attempt.attempt,
                            test_source=generated.source,
                            outcome=attempt.outcome,
                            original_summary=_execution_summary(attempt.original) or "",
                            mutant_summary=_execution_summary(attempt.mutant),
                        )
                    )

                    if result.outcome == "INVALID_ON_ORIGINAL":
                        state.invalid_attempts += 1
                        state.consecutive_invalid_attempts += 1
                        if (
                            state.consecutive_invalid_attempts
                            >= config.invalid_retry_limit
                        ):
                            state.terminal = _terminal_result(
                                state,
                                "UNRESOLVED",
                                unresolved_reason=(
                                    "consecutive invalid-on-original retry limit "
                                    f"reached ({config.invalid_retry_limit})"
                                ),
                            )
                    else:
                        state.valid_attempts += 1
                        state.consecutive_invalid_attempts = 0
                        if result.outcome == "DISTINGUISHED":
                            if result.mutant is None or (
                                result.mutant.failure is None
                                and not result.mutant.timed_out
                            ):
                                raise SandboxError(
                                    f"triage job {job_id} claimed a distinction without failure evidence"
                                )
                            state.terminal = _terminal_result(
                                state, "REAL_GAP", winning_test=generated
                            )
                        elif state.valid_attempts >= config.valid_attempts:
                            state.terminal = _terminal_result(
                                state, "PROBABLE_EQUIVALENT"
                            )

                    if state.terminal is not None:
                        _persist_terminal(artifact_dir, state.terminal)
    except SandboxError as exc:
        triage_complete = False
        for state in states:
            if state.terminal is None:
                state.terminal = _terminal_result(
                    state,
                    "UNRESOLVED",
                    unresolved_reason=f"triage sandbox infrastructure failure: {exc}",
                )
                _persist_terminal(artifact_dir, state.terminal)

    summary = _summary(states, triage_complete=triage_complete)
    _write_json(artifact_dir / "triage" / "summary.json", summary)
    return summary
