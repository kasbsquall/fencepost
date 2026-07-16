"""Records shared by Fencepost's execution and triage stages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Literal


ExecutionStatus = Literal[
    "survived", "killed", "broken", "timed_out", "infrastructure_error"
]
TriageLabel = Literal["REAL_GAP", "PROBABLE_EQUIVALENT", "UNRESOLVED"]
TriageMode = Literal["STRICT", "CONTRACT"]
AttemptOutcome = Literal[
    "INVALID_CONTRACT",
    "INVALID_ON_ORIGINAL",
    "NOT_DISTINGUISHED",
    "DISTINGUISHED",
]
AdversarialExecutionStatus = Literal[
    "passed", "failed", "timed_out", "infrastructure_error"
]
ProbeVerdict = Literal[
    "UNDERSTANDS", "PARTIAL", "MISCONCEPTION", "INSUFFICIENT"
]
ProbeStatus = Literal["READY", "GRADED", "QUESTION_FAILED", "GRADE_FAILED"]


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
    max_survivors: int | None = None


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
    author_date: str
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
class ContractViolation:
    rule: str
    line: int | None
    column: int | None
    message: str


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
    invalid_reason: str | None = None


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
    mode: TriageMode = "STRICT"
    contract_rules: dict[str, object] | None = None
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
    original: AdversarialExecution | None
    mutant: AdversarialExecution | None
    contract_violations: tuple[ContractViolation, ...] = ()


@dataclass(frozen=True)
class SurvivorTriageResult:
    mode: TriageMode
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
class TriageModeSummary:
    mode: TriageMode
    total_survivors: int
    selected_survivor_count: int
    real_gap_count: int
    probable_equivalent_count: int
    unresolved_count: int
    equivalent_rate: float | None
    triage_complete: bool
    total_attempts: int
    valid_attempts: int
    invalid_original_attempts: int
    invalid_contract_attempts: int
    generator_call_count: int
    generator_wall_clock_seconds: float
    triage_wall_clock_seconds: float
    results: tuple[SurvivorTriageResult, ...]


@dataclass(frozen=True)
class DualSurvivorTriageResult:
    mutant: MutantResult
    label_strict: TriageLabel
    label_contract: TriageLabel
    strict: SurvivorTriageResult
    contract: SurvivorTriageResult


@dataclass(frozen=True)
class ContractShieldedResult:
    mutant: MutantResult
    label_strict: TriageLabel
    label_contract: TriageLabel
    strict_winning_test: GeneratedAdversarialTest
    strict_failure_evidence: FailureEvidence
    strict_killing_attempt: AdversarialAttempt


@dataclass(frozen=True)
class TriageSummary:
    total_survivors: int
    selected_survivor_count: int
    real_gap_count_strict: int
    probable_equivalent_count_strict: int
    unresolved_count_strict: int
    equivalent_rate_strict: float | None
    real_gap_count_contract: int
    probable_equivalent_count_contract: int
    unresolved_count_contract: int
    equivalent_rate_contract: float | None
    invalid_contract_attempts: int
    triage_complete: bool
    generator_call_count: int
    generator_wall_clock_seconds: float
    triage_wall_clock_seconds: float
    strict: TriageModeSummary
    contract: TriageModeSummary
    results: tuple[DualSurvivorTriageResult, ...]
    contract_shielded: tuple[ContractShieldedResult, ...]
    probe_target_mutant_ids: tuple[str, ...]
    contract_rules: dict[str, object]
    contract_limitation: str


@dataclass(frozen=True)
class AuthoredSourceLine:
    path: str
    line: int
    text: str
    commit: str
    author_name: str
    author_email: str
    author_date: str
    commit_summary: str


@dataclass(frozen=True)
class ProbeGrounding:
    path: str
    start_line: int
    end_line: int
    authored_lines: tuple[AuthoredSourceLine, ...]
    original_segment: str
    attribution_artifact_ref: str


@dataclass(frozen=True)
class ProbeMutation:
    original_segment: str
    mutated_segment: str
    unified_diff: str


@dataclass(frozen=True)
class ProbeExecutionEvidence:
    adversarial_test: GeneratedAdversarialTest
    original_execution: AdversarialExecution
    mutant_execution: AdversarialExecution
    failing_assertion: FailureEvidence
    triage_artifact_ref: str


@dataclass(frozen=True)
class ProbeMutantEvidence:
    mutant_id: str
    mutant: MutantResult
    submitted_suite_tests_passed: int | None
    submitted_suite_artifact_ref: str
    module_path: str
    qualified_function_name: str
    original_function: str
    mutated_function: str
    mutation: ProbeMutation
    evidence: ProbeExecutionEvidence
    artifact_refs: tuple[str, ...]


@dataclass(frozen=True)
class ProbeQuestionRequest:
    site_id: str
    grounding: ProbeGrounding
    mutants: tuple[ProbeMutantEvidence, ...]


@dataclass(frozen=True)
class GeneratedProbeQuestion:
    question_text: str
    provider: str
    model: str | None
    response_id: str | None
    generation_duration_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True)
class ProbeGradeRequest:
    site_id: str
    question: GeneratedProbeQuestion
    answer: str
    grounding: ProbeGrounding
    mutants: tuple[ProbeMutantEvidence, ...]


@dataclass(frozen=True)
class GeneratedProbeGrade:
    verdict: ProbeVerdict
    feedback: str
    evidence_explanation: str
    provider: str
    model: str | None
    response_id: str | None
    generation_duration_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True)
class ProbeEvidenceCitation:
    kind: str
    nodeid: str
    message: str
    detail: str
    artifact_ref: str


@dataclass(frozen=True)
class ProbeAssessment:
    verdict: ProbeVerdict
    feedback: str
    evidence_explanation: str
    citations: tuple[ProbeEvidenceCitation, ...]
    generated: GeneratedProbeGrade


@dataclass(frozen=True)
class ProbeResult:
    site_id: str
    status: ProbeStatus
    grounding: ProbeGrounding
    survivor_count: int
    mutants: tuple[ProbeMutantEvidence, ...]
    question: GeneratedProbeQuestion | None
    answer: str | None
    assessment: ProbeAssessment | None
    error: str | None
    artifact_refs: tuple[str, ...]


@dataclass(frozen=True)
class ProbeSummary:
    total_targets: int
    total_sites: int
    accounted_mutant_count: int
    question_count: int
    submitted_answer_count: int
    graded_answer_count: int
    failed_question_count: int
    failed_grade_count: int
    complete: bool
    agent: str
    model: str | None
    call_count: int
    model_wall_clock_seconds: float
    results: tuple[ProbeResult, ...]


@dataclass(frozen=True)
class ContractShieldedReportItem:
    mutant_id: str
    path: str
    line: int
    original_segment: str
    mutated_segment: str
    reason: str
    strict_test: GeneratedAdversarialTest
    strict_failure_evidence: FailureEvidence
    artifact_refs: tuple[str, ...]


@dataclass(frozen=True)
class FencepostReport:
    schema_version: str
    title: str
    formative_notice: str
    student_name: str | None
    student_email: str
    repository_commit: str
    submitted_suite_status: str
    baseline_artifact_ref: str
    unverified_place_count: int
    question_count: int
    submitted_answer_count: int
    graded_answer_count: int
    real_gap_count_strict: int
    probable_equivalent_count_strict: int
    unresolved_count_strict: int
    equivalent_rate_strict: float | None
    real_gap_count_contract: int
    probable_equivalent_count_contract: int
    unresolved_count_contract: int
    equivalent_rate_contract: float | None
    contract_limitation: str
    places: tuple[ProbeResult, ...]
    deliberately_not_asked: tuple[ContractShieldedReportItem, ...]
    traceability_artifacts: tuple[str, ...]
    complete: bool


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
    probe: ProbeSummary | None = None
    report: FencepostReport | None = None

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
