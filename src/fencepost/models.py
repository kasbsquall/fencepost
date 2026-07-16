"""Records shared by Fencepost's first four pipeline stages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Literal


ExecutionStatus = Literal[
    "survived", "killed", "broken", "timed_out", "infrastructure_error"
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
