"""Stage 5: execution-grounded equivalence triage for surviving mutants."""

from __future__ import annotations

import ast
import difflib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable, Sequence

from .adversarial import (
    AdversarialGeneratorError,
    AdversarialTestGenerator,
)
from .contract import (
    CONTRACT_LIMITATION,
    CONTRACT_RULES,
    contract_rules_payload,
    validate_adversarial_test,
)
from .models import (
    AdversarialAttempt,
    AdversarialExecution,
    AdversarialTestRequest,
    AttemptFeedback,
    ContractShieldedResult,
    DualSurvivorTriageResult,
    GeneratedAdversarialTest,
    MutantResult,
    SurvivorTriageResult,
    TriageConfig,
    TriageJob,
    TriageJobResult,
    TriageMode,
    TriageModeSummary,
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
    mode: TriageMode
    context: SurvivorContext
    attempts: list[AdversarialAttempt] = field(default_factory=list)
    feedback: list[AttemptFeedback] = field(default_factory=list)
    generation_attempts: int = 0
    valid_attempts: int = 0
    invalid_original_attempts: int = 0
    invalid_contract_attempts: int = 0
    consecutive_invalid_attempts: int = 0
    generator_calls: int = 0
    generator_wall_clock_seconds: float = 0.0
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
        mode=state.mode,
        mutant=state.context.mutant,
        label=label,
        attempts=tuple(state.attempts),
        attempts_used=state.generation_attempts,
        valid_attempts=state.valid_attempts,
        invalid_attempts=(
            state.invalid_original_attempts + state.invalid_contract_attempts
        ),
        winning_test=winning_test,
        failure_evidence=failure,
        unresolved_reason=unresolved_reason,
    )


def _mode_root(artifact_dir: Path, mode: TriageMode) -> Path:
    return artifact_dir / "triage" / mode.lower()


def _persist_context(
    artifact_dir: Path, mode: TriageMode, context: SurvivorContext
) -> None:
    _write_json(
        _mode_root(artifact_dir, mode)
        / context.mutant.candidate.id
        / "context.json",
        {
            "mode": mode,
            "mutant": context.mutant,
            "module_path": context.module_path,
            "qualified_function_name": context.qualified_function_name,
            "original_function": context.original_function,
            "mutated_function": context.mutated_function,
            "unified_diff": context.unified_diff,
            "contract_rules": (
                contract_rules_payload(context.module_path)
                if mode == "CONTRACT"
                else None
            ),
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
        / state.mode.lower()
        / state.context.mutant.candidate.id
        / f"attempt-{attempt.attempt:02d}"
    )
    attempt_dir.mkdir(parents=True, exist_ok=True)
    (attempt_dir / "test.py").write_text(
        attempt.generated_test.source, encoding="utf-8"
    )
    _write_json(attempt_dir / "generation.json", attempt.generated_test)
    if attempt.original is not None:
        _write_json(attempt_dir / "original-result.json", attempt.original)
    if attempt.mutant is not None:
        _write_json(attempt_dir / "mutant-result.json", attempt.mutant)
    _write_json(attempt_dir / "attempt.json", attempt)


def _persist_terminal(artifact_dir: Path, result: SurvivorTriageResult) -> None:
    _write_json(
        _mode_root(artifact_dir, result.mode)
        / result.mutant.candidate.id
        / "result.json",
        result,
    )


def _mode_summary(
    states: Sequence[_SurvivorState],
    *,
    mode: TriageMode,
    triage_complete: bool,
    selected_survivor_count: int,
    triage_wall_clock_seconds: float,
) -> TriageModeSummary:
    results = tuple(state.terminal for state in states if state.terminal is not None)
    real_gaps = sum(result.label == "REAL_GAP" for result in results)
    equivalents = sum(result.label == "PROBABLE_EQUIVALENT" for result in results)
    unresolved = sum(result.label == "UNRESOLVED" for result in results)
    decided = real_gaps + equivalents
    rate = equivalents / decided if triage_complete and decided else None
    return TriageModeSummary(
        mode=mode,
        total_survivors=len(states),
        selected_survivor_count=selected_survivor_count,
        real_gap_count=real_gaps,
        probable_equivalent_count=equivalents,
        unresolved_count=unresolved,
        equivalent_rate=rate,
        triage_complete=triage_complete,
        total_attempts=sum(state.generation_attempts for state in states),
        valid_attempts=sum(state.valid_attempts for state in states),
        invalid_original_attempts=sum(
            state.invalid_original_attempts for state in states
        ),
        invalid_contract_attempts=sum(
            state.invalid_contract_attempts for state in states
        ),
        generator_call_count=sum(state.generator_calls for state in states),
        generator_wall_clock_seconds=sum(
            state.generator_wall_clock_seconds for state in states
        ),
        triage_wall_clock_seconds=triage_wall_clock_seconds,
        results=results,
    )


def _initialize_states(
    survivors: Sequence[SurvivorContext],
    *,
    mode: TriageMode,
    artifact_dir: Path,
    config: TriageConfig,
) -> tuple[list[_SurvivorState], int]:
    states = [_SurvivorState(mode=mode, context=context) for context in survivors]
    selected_survivor_count = (
        len(states)
        if config.max_survivors is None
        else min(len(states), config.max_survivors)
    )
    for index, state in enumerate(states):
        _persist_context(artifact_dir, mode, state.context)
        if index >= selected_survivor_count:
            state.terminal = _terminal_result(
                state,
                "UNRESOLVED",
                unresolved_reason=(
                    "not selected because the configured maximum survivors "
                    f"triaged is {config.max_survivors}"
                ),
            )
            _persist_terminal(artifact_dir, state.terminal)
    return states, selected_survivor_count


def _invalid_reason(attempt: AdversarialAttempt) -> str | None:
    if not attempt.contract_violations:
        return None
    return "; ".join(
        f"{item.rule} at line {item.line}: {item.message}"
        for item in attempt.contract_violations
    )


def _finish_invalid_attempt(
    state: _SurvivorState,
    *,
    config: TriageConfig,
    artifact_dir: Path,
    kind: str,
) -> None:
    state.consecutive_invalid_attempts += 1
    if state.consecutive_invalid_attempts < config.invalid_retry_limit:
        return
    state.terminal = _terminal_result(
        state,
        "UNRESOLVED",
        unresolved_reason=(
            f"consecutive invalid retry limit reached ({config.invalid_retry_limit}); "
            f"last invalid outcome was {kind}"
        ),
    )
    _persist_terminal(artifact_dir, state.terminal)


def _run_mode(
    states: Sequence[_SurvivorState],
    *,
    mode: TriageMode,
    generator: AdversarialTestGenerator,
    execute_round: Callable[[list[TriageJob]], dict[str, TriageJobResult]],
    artifact_dir: Path,
    config: TriageConfig,
) -> None:
    while any(state.terminal is None for state in states):
        jobs: list[TriageJob] = []
        pending: dict[str, tuple[_SurvivorState, GeneratedAdversarialTest]] = {}
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
                mode=mode,
                contract_rules=(
                    contract_rules_payload(state.context.module_path)
                    if mode == "CONTRACT"
                    else None
                ),
                prior_attempts=tuple(state.feedback),
            )
            state.generator_calls += 1
            generation_started = time.monotonic()
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
            finally:
                state.generator_wall_clock_seconds += (
                    time.monotonic() - generation_started
                )

            validation = validate_adversarial_test(
                generated.source,
                module_path=state.context.module_path,
                mode=mode,
            )
            if not validation.accepted:
                attempt = AdversarialAttempt(
                    attempt=state.generation_attempts,
                    valid_attempt_number=None,
                    generated_test=generated,
                    outcome="INVALID_CONTRACT",
                    original=None,
                    mutant=None,
                    contract_violations=validation.violations,
                )
                state.attempts.append(attempt)
                state.invalid_contract_attempts += 1
                _persist_attempt(artifact_dir, state, attempt)
                reason = _invalid_reason(attempt)
                state.feedback.append(
                    AttemptFeedback(
                        attempt=attempt.attempt,
                        test_source=generated.source,
                        outcome=attempt.outcome,
                        original_summary="not executed: rejected by CONTRACT AST validator",
                        mutant_summary=None,
                        invalid_reason=reason,
                    )
                )
                _finish_invalid_attempt(
                    state,
                    config=config,
                    artifact_dir=artifact_dir,
                    kind="INVALID_CONTRACT",
                )
                continue

            job_id = (
                f"{mode.lower()}-{state.context.mutant.candidate.id}"
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
        batch = execute_round(jobs)
        missing = set(pending).difference(batch)
        if missing:
            raise SandboxError(
                "triage session omitted job results: " + ", ".join(sorted(missing))
            )

        for job_id, (state, generated) in pending.items():
            result = batch[job_id]
            if result.outcome not in {
                "INVALID_ON_ORIGINAL",
                "NOT_DISTINGUISHED",
                "DISTINGUISHED",
            }:
                raise SandboxError(
                    f"triage job {job_id} returned invalid driver outcome {result.outcome!r}"
                )
            if (
                result.outcome != "INVALID_ON_ORIGINAL"
                and result.original.status != "passed"
            ):
                raise SandboxError(
                    f"triage job {job_id} treated a non-passing original as valid"
                )
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
                state.invalid_original_attempts += 1
                _finish_invalid_attempt(
                    state,
                    config=config,
                    artifact_dir=artifact_dir,
                    kind="INVALID_ON_ORIGINAL",
                )
                continue

            state.valid_attempts += 1
            state.consecutive_invalid_attempts = 0
            if result.outcome == "DISTINGUISHED":
                if result.mutant is None or (
                    result.mutant.failure is None and not result.mutant.timed_out
                ):
                    raise SandboxError(
                        f"triage job {job_id} claimed a distinction without failure evidence"
                    )
                state.terminal = _terminal_result(
                    state, "REAL_GAP", winning_test=generated
                )
            else:
                if result.mutant is None or result.mutant.status != "passed":
                    raise SandboxError(
                        f"triage job {job_id} claimed no distinction without a passing mutant"
                    )
                if state.valid_attempts >= config.valid_attempts:
                    state.terminal = _terminal_result(
                        state, "PROBABLE_EQUIVALENT"
                    )

            if state.terminal is not None:
                _persist_terminal(artifact_dir, state.terminal)


def _mark_infrastructure_failure(
    states: Sequence[_SurvivorState], *, artifact_dir: Path, error: SandboxError
) -> None:
    for state in states:
        if state.terminal is not None:
            continue
        state.terminal = _terminal_result(
            state,
            "UNRESOLVED",
            unresolved_reason=f"triage sandbox infrastructure failure: {error}",
        )
        _persist_terminal(artifact_dir, state.terminal)


def _aggregate_summary(
    strict: TriageModeSummary,
    contract: TriageModeSummary,
    *,
    triage_wall_clock_seconds: float,
) -> TriageSummary:
    contract_by_id = {
        result.mutant.candidate.id: result for result in contract.results
    }
    paired: list[DualSurvivorTriageResult] = []
    shielded: list[ContractShieldedResult] = []
    for strict_result in strict.results:
        candidate_id = strict_result.mutant.candidate.id
        contract_result = contract_by_id[candidate_id]
        paired.append(
            DualSurvivorTriageResult(
                mutant=strict_result.mutant,
                label_strict=strict_result.label,
                label_contract=contract_result.label,
                strict=strict_result,
                contract=contract_result,
            )
        )
        if (
            strict_result.label == "REAL_GAP"
            and contract_result.label == "PROBABLE_EQUIVALENT"
        ):
            killing_attempt = next(
                attempt
                for attempt in reversed(strict_result.attempts)
                if attempt.outcome == "DISTINGUISHED"
            )
            if (
                strict_result.winning_test is None
                or strict_result.failure_evidence is None
            ):
                raise ValueError(
                    f"strict real gap {candidate_id} lacks its evidence pair"
                )
            shielded.append(
                ContractShieldedResult(
                    mutant=strict_result.mutant,
                    label_strict=strict_result.label,
                    label_contract=contract_result.label,
                    strict_winning_test=strict_result.winning_test,
                    strict_failure_evidence=strict_result.failure_evidence,
                    strict_killing_attempt=killing_attempt,
                )
            )

    contract_rules = json_value(CONTRACT_RULES)
    contract_rules["module_under_test"] = "resolved independently per survivor"
    return TriageSummary(
        total_survivors=strict.total_survivors,
        selected_survivor_count=strict.selected_survivor_count,
        real_gap_count_strict=strict.real_gap_count,
        probable_equivalent_count_strict=strict.probable_equivalent_count,
        unresolved_count_strict=strict.unresolved_count,
        equivalent_rate_strict=strict.equivalent_rate,
        real_gap_count_contract=contract.real_gap_count,
        probable_equivalent_count_contract=contract.probable_equivalent_count,
        unresolved_count_contract=contract.unresolved_count,
        equivalent_rate_contract=contract.equivalent_rate,
        invalid_contract_attempts=contract.invalid_contract_attempts,
        triage_complete=strict.triage_complete and contract.triage_complete,
        generator_call_count=(
            strict.generator_call_count + contract.generator_call_count
        ),
        generator_wall_clock_seconds=(
            strict.generator_wall_clock_seconds
            + contract.generator_wall_clock_seconds
        ),
        triage_wall_clock_seconds=triage_wall_clock_seconds,
        strict=strict,
        contract=contract,
        results=tuple(paired),
        contract_shielded=tuple(shielded),
        probe_target_mutant_ids=tuple(
            result.mutant.candidate.id
            for result in contract.results
            if result.label == "REAL_GAP"
        ),
        contract_rules=contract_rules,
        contract_limitation=CONTRACT_LIMITATION,
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
    """Triage every survivor independently in STRICT and CONTRACT modes."""
    triage_started = time.monotonic()
    if config.valid_attempts < 1:
        raise ValueError("valid attempt budget must be at least 1")
    if config.invalid_retry_limit < 1:
        raise ValueError("invalid retry limit must be at least 1")
    if config.test_timeout_seconds <= 0:
        raise ValueError("triage test timeout must be positive")
    if config.max_survivors is not None and config.max_survivors < 1:
        raise ValueError("maximum survivors triaged must be at least 1")

    strict_states, selected = _initialize_states(
        survivors,
        mode="STRICT",
        artifact_dir=artifact_dir,
        config=config,
    )
    contract_states, contract_selected = _initialize_states(
        survivors,
        mode="CONTRACT",
        artifact_dir=artifact_dir,
        config=config,
    )
    if selected != contract_selected:
        raise ValueError("strict and contract survivor selection diverged")

    strict_complete = True
    contract_complete = True
    strict_wall = 0.0
    contract_wall = 0.0
    needs_execution = any(
        state.terminal is None for state in (*strict_states, *contract_states)
    )
    if needs_execution:
        import_roots = sandbox.import_roots(baseline_tree)
        session_input = artifact_dir / "triage" / "session-input"
        session_output = artifact_dir / "triage" / "session-output"
        session_input.mkdir(parents=True, exist_ok=True)
        session_output.mkdir(parents=True, exist_ok=True)
        round_id = 0
        phase: TriageMode = "STRICT"
        mode_started = time.monotonic()
        try:
            with sandbox.triage_session(
                baseline_tree,
                session_input,
                session_output,
                import_roots=import_roots,
                workers=workers,
                per_test_timeout=config.test_timeout_seconds,
            ) as session:

                def execute_round(
                    jobs: list[TriageJob],
                ) -> dict[str, TriageJobResult]:
                    nonlocal round_id
                    round_id += 1
                    return session.run_round(round_id, jobs)

                _run_mode(
                    strict_states,
                    mode="STRICT",
                    generator=generator,
                    execute_round=execute_round,
                    artifact_dir=artifact_dir,
                    config=config,
                )
                strict_wall = time.monotonic() - mode_started
                phase = "CONTRACT"
                mode_started = time.monotonic()
                _run_mode(
                    contract_states,
                    mode="CONTRACT",
                    generator=generator,
                    execute_round=execute_round,
                    artifact_dir=artifact_dir,
                    config=config,
                )
                contract_wall = time.monotonic() - mode_started
        except SandboxError as exc:
            if phase == "STRICT":
                strict_wall = time.monotonic() - mode_started
                strict_complete = False
                contract_complete = False
                _mark_infrastructure_failure(
                    strict_states, artifact_dir=artifact_dir, error=exc
                )
            else:
                contract_wall = time.monotonic() - mode_started
                contract_complete = False
            _mark_infrastructure_failure(
                contract_states, artifact_dir=artifact_dir, error=exc
            )

    strict_summary = _mode_summary(
        strict_states,
        mode="STRICT",
        triage_complete=strict_complete,
        selected_survivor_count=selected,
        triage_wall_clock_seconds=strict_wall,
    )
    contract_summary = _mode_summary(
        contract_states,
        mode="CONTRACT",
        triage_complete=contract_complete,
        selected_survivor_count=selected,
        triage_wall_clock_seconds=contract_wall,
    )
    _write_json(_mode_root(artifact_dir, "STRICT") / "summary.json", strict_summary)
    _write_json(
        _mode_root(artifact_dir, "CONTRACT") / "summary.json", contract_summary
    )
    summary = _aggregate_summary(
        strict_summary,
        contract_summary,
        triage_wall_clock_seconds=time.monotonic() - triage_started,
    )
    _write_json(artifact_dir / "triage" / "summary.json", summary)
    return summary
