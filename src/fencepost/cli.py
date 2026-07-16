"""Command-line entry point for the stage 1-4 engine."""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path

from .models import RunConfig
from .pipeline import PipelineError, run_analysis


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fencepost",
        description="Attribute, select, mutate, and execute a Python pytest submission.",
        epilog=(
            "Scope: committed projects using only the standard library and pytest. "
            "Fencepost adds the repository root, conventional src/, and detected top-level packages to PYTHONPATH; "
            "it does not install requirements.txt, pyproject, or setup.py dependencies, or support custom build layouts."
        ),
    )
    parser.add_argument("repo", type=Path, help="Committed student Git repository")
    parser.add_argument("--student-email", required=True, help="Git author email for the student")
    parser.add_argument("--output", type=Path, required=True, help="Empty directory for run artifacts")
    parser.add_argument("--commit", default="HEAD", help="Commit to analyse (default: HEAD)")
    parser.add_argument("--image", default="fencepost-runner:local", help="Docker runner image")
    parser.add_argument(
        "--workers",
        type=int,
        help="Concurrent pytest subprocesses inside the batch container (default: up to 4)",
    )
    parser.add_argument(
        "--no-build-image",
        action="store_true",
        help="Require the runner image to already exist",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = RunConfig(
        repo=args.repo,
        student_email=args.student_email,
        artifact_dir=args.output,
        commit=args.commit,
        image=args.image,
        mutant_workers=args.workers,
        build_image=not args.no_build_image,
    )
    try:
        result = run_analysis(config)
    except PipelineError as exc:
        print(f"fencepost: {exc}")
        return 2
    statuses: dict[str, int] = {}
    for mutant in result.mutant_results:
        status = mutant.execution.status
        statuses[status] = statuses.get(status, 0) + 1
    durations = [mutant.execution.duration_seconds for mutant in result.mutant_results]
    median = statistics.median(durations) if durations else 0.0
    print(
        f"{result.mutant_count} mutants in {result.elapsed_seconds:.2f}s "
        f"(batch {result.batch_duration_seconds:.2f}s, "
        f"workers {result.mutant_workers}, median {median:.2f}s/mutant) "
        + " ".join(f"{status}={count}" for status, count in sorted(statuses.items()))
    )
    print(f"artifact: {result.artifact_dir}")
    return 0
