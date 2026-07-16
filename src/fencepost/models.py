"""Records shared by Fencepost's execution and triage stages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Literal


ExecutionStatus = Literal[
    "survived", "killed", "broken", "timed_out", "infrastructure_error"
]
TriageLabel = Literal["REAL_GAP", "PROBABLE_EQUIVALENT", "UNRESOLVED"]
AttemptOutcome = Literal[
    "INVALID_ON_ORIGINAL", "NOT_DISTINGUISHED", "DISTINGUISHED"
]
AdversarialExecutionStatus = Literal[
    "passed", "failed", "timed_out", "infrastructure_error"
]


@dataclass(frozen=True)
class RunConfig:
    repo: Path
    student_email: str
    artifact_dir: Path
    commit: str = "HEAD"
    image: str = "fencepost-runner:local"
    baseline_timeout_seconds: float = 60.0
    mutant_timeout_cap_seconds: float = 60.0
    mutant_workers: int | None = None
    build_image: bool = True


@dataclass(frozen=True)
class TriageConfig:
    valid_attempts: int = 3
    invalid_retry_limit: int = 3
    test_timeout_seconds: float = 10.0


@dataclass(frozen=True)
class SourceSpan:
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass(frozen=True)
class PathStep:
    field: str
    index: int | None = None


@dataclass(frozen=True)
class BlameLine:
    path: str
    line: int
    commit: str
    author_name: str
    author_email: str
    summary: str
    is_student: bool


@dataclass(frozen=True)
class MutationCandidate:
    id: str
    path: str
    anchor: SourceSpan
    ast_path: tuple[PathStep, ...]
    kind: str
    before: str
    after: str
    source_segment: str
    parameters: tuple[tuple[str, str], ...] = ()

    @property
    def parameter_map(self) -> dict[str, str]:
        return dict(self.parameters)


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    exit_code: int | None
    duration_seconds: float
    stdout: str
    stderr: str
    timed_out: bool = False
    failing_tests: tuple[str, ...] = ()


@dataclass(frozen=True)
class MutantResult:
    candidate: MutationCandidate
    generated_anchor: SourceSpan
    execution: ExecutionResult


@dataclass(frozen=True)
class FailureEvidence:
    nodeid: str
    kind: str
    message: str
    detail: str


@dataclass(frozen=True)
class AdversarialExecution:
    status: AdversarialExecutionStatus
    exit_code: int | None
    duration_seconds: float
    stdout: str
    stderr: str
    timed_out: bool = False
    tests_collected: int = 0
    tests_skipped: int = 0
    failure: FailureEvidence | None = None


@dataclass(frozen=True)
class AttemptFeedback:
    attempt: int
    test_source: str
    outcome: AttemptOutcome
    original_summary: str
    mutant_summary: str | None = None


@dataclass(frozen=True)
class AdversarialTestRequest:
    mutant: MutantResult
    attempt: int
    valid_attempts_completed: int
    module_path: str
    qualified_function_name: str
    original_function: str
    mutated_function: str
    unified_diff: str
    prior_attempts: tuple[AttemptFeedback, ...] = ()


@dataclass(frozen=True)
class GeneratedAdversarialTest:
    source: str
    targeted_behavior: str
    provider: str
    model: str | None
    response_id: str | None
    generation_duration_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True)
class TriageJob:
    id: str
    mutant_path: str
    mutant_source: str
    test_source: str
    attempt: int


@dataclass(frozen=True)
class TriageJobResult:
    id: str
    outcome: AttemptOutcome
    original: AdversarialExecution
    mutant: AdversarialExecution | None


@dataclass(frozen=True)
class AdversarialAttempt:
    attempt: int
    valid_attempt_number: int | None
    generated_test: GeneratedAdversarialTest
    outcome: AttemptOutcome
    original: AdversarialExecution
    mutant: AdversarialExecution | None


@dataclass(frozen=True)
class SurvivorTriageResult:
    mutant: MutantResult
    label: TriageLabel
    attempts: tuple[AdversarialAttempt, ...]
    attempts_used: int
    valid_attempts: int
    invalid_attempts: int
    winning_test: GeneratedAdversarialTest | None
    failure_evidence: FailureEvidence | None
    unresolved_reason: str | None = None


@dataclass(frozen=True)
class TriageSummary:
    total_survivors: int
    real_gap_count: int
    probable_equivalent_count: int
    unresolved_count: int
    equivalent_rate: float | None
    triage_complete: bool
    total_attempts: int
    valid_attempts: int
    invalid_original_attempts: int
    results: tuple[SurvivorTriageResult, ...]


@dataclass(frozen=True)
class AnalysisResult:
    repo: Path
    commit: str
    baseline_duration_seconds: float
    covered_lines: dict[str, tuple[int, ...]]
    mutant_results: tuple[MutantResult, ...]
    mutant_workers: int
    batch_duration_seconds: float
    elapsed_seconds: float
    artifact_dir: Path
    triage: TriageSummary | None = None

    @property
    def mutant_count(self) -> int:
        return len(self.mutant_results)


def json_value(value: Any) -> Any:
    """Convert the run records into JSON-safe values without custom encoders."""
    if is_dataclass(value):
        return {key: json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [json_value(item) for item in value]
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    return value
