"""Command-line entry point for the Fencepost analysis engine."""

from __future__ import annotations

import argparse
import os
import statistics
from pathlib import Path

from .adversarial import AdversarialGeneratorError, OpenAIAdversarialTestGenerator
from .models import RunConfig, TriageConfig
from .pipeline import PipelineError, run_analysis


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fencepost",
        description=(
            "Attribute, select, mutate, execute, and triage a Python pytest submission."
        ),
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
    parser.add_argument(
        "--adversarial-model",
        default=os.environ.get("FENCEPOST_ADVERSARIAL_MODEL"),
        help=(
            "OpenAI model for adversarial test generation "
            "(or FENCEPOST_ADVERSARIAL_MODEL)"
        ),
    )
    parser.add_argument(
        "--triage-attempts",
        type=int,
        default=3,
        help="Required valid original-pass/mutant-run attempts (default: 3)",
    )
    parser.add_argument(
        "--invalid-retries",
        type=int,
        default=3,
        help="Consecutive invalid-on-original retry limit (default: 3)",
    )
    parser.add_argument(
        "--skip-triage",
        action="store_true",
        help="Run only stages 1-4 without model calls",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if not args.skip_triage and not args.adversarial_model:
        parser.error(
            "--adversarial-model or FENCEPOST_ADVERSARIAL_MODEL is required "
            "unless --skip-triage is used"
        )
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
        generator = (
            None
            if args.skip_triage
            else OpenAIAdversarialTestGenerator(model=args.adversarial_model)
        )
        triage_config = (
            None
            if args.skip_triage
            else TriageConfig(
                valid_attempts=args.triage_attempts,
                invalid_retry_limit=args.invalid_retries,
            )
        )
        result = run_analysis(
            config,
            adversarial_generator=generator,
            triage_config=triage_config,
        )
    except (PipelineError, AdversarialGeneratorError, ValueError) as exc:
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
    if result.triage is not None:
        triage = result.triage
        rate = (
            "null"
            if triage.equivalent_rate is None
            else f"{triage.equivalent_rate:.3f}"
        )
        print(
            f"triage: survivors={triage.total_survivors} "
            f"real_gap={triage.real_gap_count} "
            f"probable_equivalent={triage.probable_equivalent_count} "
            f"unresolved={triage.unresolved_count} "
            f"equivalent_rate={rate} complete={triage.triage_complete}"
        )
    print(f"artifact: {result.artifact_dir}")
    return 0 if result.triage is None or result.triage.triage_complete else 3
