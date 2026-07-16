"""Command-line entry point for the Fencepost analysis engine."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

from .adversarial import (
    AdversarialGeneratorError,
    CodexCliAdversarialTestGenerator,
    OpenAIAdversarialTestGenerator,
)
from .models import RunConfig, TriageConfig
from .pipeline import PipelineError, run_analysis
from .probe import CodexCliComprehensionProbeAgent


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fencepost",
        description=(
            "Attribute, select, mutate, execute, triage, probe, and report on a Python pytest submission."
        ),
        epilog=(
            "Use 'fencepost serve ARTIFACT_DIR' to open the read-only report UI. "
            "Scope: committed projects using only the standard library and pytest. "
            "Fencepost adds the repository root, conventional src/, and detected top-level packages to PYTHONPATH; "
            "it does not install requirements.txt, pyproject, or setup.py dependencies, or support custom build layouts. "
            "Real triage runs both STRICT and CONTRACT modes and makes one model call per generated test; it can take "
            "several minutes and consumes the selected "
            "provider's usage allowance; use --triage-attempts and --max-survivors-triaged to bound a demo."
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
        "--generator",
        choices=("codex", "openai", "fake"),
        default="codex",
        help="Adversarial-test generator (default: codex with ChatGPT authentication)",
    )
    parser.add_argument(
        "--adversarial-model",
        default=os.environ.get("FENCEPOST_ADVERSARIAL_MODEL", "gpt-5.6-terra"),
        help=(
            "Exact provider model slug (default: gpt-5.6-terra; "
            "or FENCEPOST_ADVERSARIAL_MODEL)"
        ),
    )
    parser.add_argument(
        "--generator-timeout",
        type=float,
        default=300.0,
        help="Per-generation Codex CLI timeout in seconds (default: 300)",
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
        "--max-survivors-triaged",
        type=int,
        help=(
            "Triages only the first N survivors; the rest are visibly UNRESOLVED "
            "(default: all)"
        ),
    )
    parser.add_argument(
        "--skip-triage",
        action="store_true",
        help="Run only stages 1-4 without model calls",
    )
    parser.add_argument(
        "--skip-probe",
        action="store_true",
        help="Run through Stage 5 but do not generate questions or a report",
    )
    parser.add_argument(
        "--answers",
        type=Path,
        help=(
            "JSON object mapping probe site IDs to typed student answers "
            "(a member mutant ID is also accepted for compatibility)"
        ),
    )
    return parser


def _build_generator(args):
    if args.generator == "codex":
        if args.adversarial_model == "gpt-5.6":
            raise ValueError(
                "ChatGPT-auth Codex rejects 'gpt-5.6'; use gpt-5.6-terra or gpt-5.6-sol"
            )
        return CodexCliAdversarialTestGenerator(
            model=args.adversarial_model,
            timeout_seconds=args.generator_timeout,
        )
    if args.generator == "openai":
        return OpenAIAdversarialTestGenerator(model=args.adversarial_model)
    try:
        from tests.fakes import FixtureAdversarialTestGenerator
    except ImportError as exc:
        raise AdversarialGeneratorError(
            "the fake generator is available only from a Fencepost source checkout"
        ) from exc
    return FixtureAdversarialTestGenerator()


def _build_probe_agent(args, adversarial_generator):
    if args.generator == "fake":
        try:
            from tests.fakes import FixtureComprehensionProbeAgent
        except ImportError as exc:
            raise AdversarialGeneratorError(
                "the fake probe agent is available only from a Fencepost source checkout"
            ) from exc
        return FixtureComprehensionProbeAgent()
    if args.generator != "codex":
        raise ValueError(
            "Stage 6 uses the ChatGPT-authenticated Codex CLI; use --generator codex "
            "or add --skip-probe when selecting the OpenAI adversarial-test option"
        )
    return CodexCliComprehensionProbeAgent(
        model=args.adversarial_model,
        client=adversarial_generator.client,
    )


def _load_answers(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read probe answers {path}: {exc}") from exc
    if not isinstance(payload, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in payload.items()
    ):
        raise ValueError("probe answers must be a JSON object of string IDs to strings")
    return payload


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    if raw_args[:1] == ["serve"]:
        from .serve import main as serve_main

        return serve_main(raw_args[1:])
    parser = _parser()
    args = parser.parse_args(raw_args)
    if not args.skip_triage and not args.adversarial_model:
        parser.error(
            "--adversarial-model or FENCEPOST_ADVERSARIAL_MODEL is required "
            "unless --skip-triage is used"
        )
    if args.skip_triage and args.answers is not None:
        parser.error("--answers cannot be used with --skip-triage")
    if args.skip_probe and args.answers is not None:
        parser.error("--answers cannot be used with --skip-probe")
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
        generator = None if args.skip_triage else _build_generator(args)
        probe_agent = (
            None
            if args.skip_triage or args.skip_probe
            else _build_probe_agent(args, generator)
        )
        answers = _load_answers(args.answers)
        triage_config = (
            None
            if args.skip_triage
            else TriageConfig(
                valid_attempts=args.triage_attempts,
                invalid_retry_limit=args.invalid_retries,
                max_survivors=args.max_survivors_triaged,
            )
        )
        result = run_analysis(
            config,
            adversarial_generator=generator,
            triage_config=triage_config,
            probe_agent=probe_agent,
            probe_answers=answers,
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
        strict_rate = (
            "null"
            if triage.equivalent_rate_strict is None
            else f"{triage.equivalent_rate_strict:.3f}"
        )
        contract_rate = (
            "null"
            if triage.equivalent_rate_contract is None
            else f"{triage.equivalent_rate_contract:.3f}"
        )
        print(
            f"triage STRICT: survivors={triage.total_survivors} "
            f"selected={triage.selected_survivor_count} "
            f"real_gap={triage.real_gap_count_strict} "
            f"probable_equivalent={triage.probable_equivalent_count_strict} "
            f"unresolved={triage.unresolved_count_strict} "
            f"equivalent_rate_strict={strict_rate}"
        )
        print(
            f"triage CONTRACT: survivors={triage.total_survivors} "
            f"selected={triage.selected_survivor_count} "
            f"real_gap={triage.real_gap_count_contract} "
            f"probable_equivalent={triage.probable_equivalent_count_contract} "
            f"unresolved={triage.unresolved_count_contract} "
            f"invalid_contract={triage.invalid_contract_attempts} "
            f"equivalent_rate_contract={contract_rate} "
            f"contract_shielded={len(triage.contract_shielded)} "
            f"complete={triage.triage_complete}"
        )
        print(f"CONTRACT limitation: {triage.contract_limitation}")
        print(
            f"generation: calls={triage.generator_call_count} "
            f"model_wall={triage.generator_wall_clock_seconds:.2f}s "
            f"triage_wall={triage.triage_wall_clock_seconds:.2f}s; "
            "each call has Codex startup/model latency and consumes ChatGPT usage "
            "when --generator codex is selected"
        )
    if result.probe is not None:
        print(
            f"probe: mutants={result.probe.total_targets} "
            f"sites={result.probe.total_sites} "
            f"accounted={result.probe.accounted_mutant_count} "
            f"questions={result.probe.question_count} "
            f"answers={result.probe.submitted_answer_count} "
            f"graded={result.probe.graded_answer_count} "
            f"calls={result.probe.call_count} "
            f"model_wall={result.probe.model_wall_clock_seconds:.2f}s "
            f"complete={result.probe.complete}"
        )
    if result.report is not None:
        print(f"report: {result.artifact_dir / 'report' / 'report.json'}")
    print(f"artifact: {result.artifact_dir}")
    complete = result.triage is None or result.triage.triage_complete
    if result.probe is not None:
        complete = complete and result.probe.complete
    return 0 if complete else 3
