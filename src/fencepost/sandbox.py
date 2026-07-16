"""Docker-only test execution for the first Fencepost build.

Student code is never executed by the host Python process.  The host performs
Git and AST work, then mounts a read-only staged tree into Docker. Mutants share
one batch container but receive separate writable trees and bytecode caches.
"""

from __future__ import annotations

import json
import math
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .models import ExecutionResult


class SandboxError(RuntimeError):
    pass


@dataclass(frozen=True)
class BaselineRun:
    execution: ExecutionResult
    covered_lines: dict[str, tuple[int, ...]]


@dataclass(frozen=True)
class BatchRun:
    results: dict[str, ExecutionResult]
    aborted_all_broken: bool
    container_duration_seconds: float


@dataclass(frozen=True)
class _ContainerRun:
    exit_code: int | None
    duration_seconds: float
    stdout: str
    stderr: str
    timed_out: bool = False


class DockerSandbox:
    """Minimal Docker client with bounded runs and explicit resource limits."""

    def __init__(self, image: str, project_root: Path, build_image: bool = True) -> None:
        self.image = image
        self.project_root = project_root
        self.build_image = build_image

    def ensure_image(self) -> None:
        try:
            probe = subprocess.run(
                ["docker", "image", "inspect", self.image],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SandboxError(
                "Docker is unavailable; start a working Docker daemon before running Fencepost"
            ) from exc
        if probe.returncode == 0 and not self.build_image:
            return
        if not self.build_image:
            raise SandboxError(
                f"Docker image {self.image!r} is absent and automatic image building is disabled"
            )
        # A cached build is cheap and ensures Dockerfile changes (notably
        # sandbox environment fixes) are reflected in the tagged local image.
        try:
            built = subprocess.run(
                [
                    "docker",
                    "build",
                    "--file",
                    str(self.project_root / "docker" / "runner.Dockerfile"),
                    "--tag",
                    self.image,
                    str(self.project_root),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=300,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SandboxError("failed to build Fencepost runner image") from exc
        if built.returncode != 0:
            raise SandboxError(
                "failed to build Fencepost runner image:\n"
                + (built.stdout + "\n" + built.stderr).strip()
            )

    def baseline(self, source_tree: Path, output_dir: Path, timeout: float) -> BaselineRun:
        execution = self._run("baseline", source_tree, output_dir, timeout)
        if execution.status != "survived":
            raise SandboxError(
                "the submitted pytest suite must pass before mutation; "
                f"got {execution.status} (exit {execution.exit_code})\n{execution.stdout}\n{execution.stderr}"
            )
        coverage_path = output_dir / "coverage.json"
        if not coverage_path.exists():
            raise SandboxError("baseline runner did not produce coverage.json")
        try:
            payload = json.loads(coverage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SandboxError(f"invalid coverage.json: {exc}") from exc
        covered: dict[str, tuple[int, ...]] = {}
        for filename, details in payload.get("files", {}).items():
            normalized = self._coverage_path(filename, source_tree)
            executed = tuple(sorted(set(details.get("executed_lines", []))))
            covered[normalized] = executed
        return BaselineRun(execution=execution, covered_lines=covered)

    @staticmethod
    def _coverage_path(filename: str, source_tree: Path) -> str:
        value = Path(filename)
        if value.is_absolute():
            try:
                return value.resolve().relative_to(source_tree.resolve()).as_posix()
            except ValueError:
                return value.as_posix()
        return value.as_posix()

    def mutant(self, source_tree: Path, output_dir: Path, timeout: float) -> ExecutionResult:
        return self._run("mutant", source_tree, output_dir, timeout)

    def batch(
        self,
        source_tree: Path,
        input_dir: Path,
        output_dir: Path,
        *,
        mutant_count: int,
        per_mutant_timeout: float,
        workers: int,
    ) -> BatchRun:
        """Run all generated mutants in one hardened batch container."""
        source_tree = source_tree.resolve()
        input_dir = input_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        name = f"fencepost-batch-{uuid.uuid4().hex[:12]}"
        memory_mb = min(4096, max(512, workers * 256))
        pids = max(128, workers * 32)
        command = self._container_command(
            name=name,
            cpus=workers,
            memory=f"{memory_mb}m",
            pids=pids,
        ) + [
            "--tmpfs",
            "/work:rw,nosuid,size=512m",
            "--workdir",
            "/baseline",
            "--mount",
            f"type=bind,src={source_tree},dst=/baseline,readonly",
            "--mount",
            f"type=bind,src={input_dir},dst=/input,readonly",
            "--mount",
            f"type=bind,src={output_dir.resolve()},dst=/out",
            self.image,
            "batch",
        ]
        rounds = max(1, math.ceil(mutant_count / workers))
        container_timeout = max(60.0, (rounds * per_mutant_timeout) + 30.0)
        raw = self._execute_container(command, name, container_timeout)
        result_path = output_dir / "batch-results.json"
        if raw.timed_out:
            raise SandboxError(
                f"mutant batch container exceeded {container_timeout:.1f}s and was killed"
            )
        if raw.exit_code not in (0, 12) or not result_path.exists():
            raise SandboxError(
                "mutant batch driver failed; "
                f"exit={raw.exit_code}\nstdout:\n{raw.stdout}\nstderr:\n{raw.stderr}"
            )
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SandboxError(f"invalid batch-results.json: {exc}") from exc
        results = {
            mutant_id: ExecutionResult(
                status=value["status"],
                exit_code=value.get("exit_code"),
                duration_seconds=float(value["duration_seconds"]),
                stdout=value.get("stdout", ""),
                stderr=value.get("stderr", ""),
                timed_out=bool(value.get("timed_out", False)),
                failing_tests=tuple(value.get("failing_tests", ())),
            )
            for mutant_id, value in payload.get("results", {}).items()
        }
        return BatchRun(
            results=results,
            aborted_all_broken=bool(payload.get("aborted_all_broken", False)),
            container_duration_seconds=raw.duration_seconds,
        )

    def preflight(self, source_tree: Path, output_dir: Path, timeout: float) -> None:
        """Validate the read-only runner against the unmodified submission.

        This invokes the same compile, collect, and pytest sequence used for a
        mutant before spending time on any candidates.  A failure here is a
        harness failure, not evidence about a student's code.
        """
        execution = self.mutant(source_tree, output_dir, timeout)
        if execution.status != "survived":
            raise SandboxError(
                "sandbox preflight failed on the unmodified submission; "
                "the mutant harness is unusable. "
                f"status={execution.status}, exit={execution.exit_code}\n"
                f"stdout:\n{execution.stdout}\nstderr:\n{execution.stderr}"
            )

    def _run(
        self, mode: str, source_tree: Path, output_dir: Path, timeout: float
    ) -> ExecutionResult:
        source_tree = source_tree.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        name = f"fencepost-{uuid.uuid4().hex[:12]}"
        command = self._container_command(
            name=name, cpus=1, memory="512m", pids=128
        ) + [
            "--workdir",
            "/workspace",
            "--env",
            f"PYTHONPATH={self._pythonpath(source_tree)}",
            "--mount",
            f"type=bind,src={source_tree},dst=/workspace,readonly",
            "--mount",
            f"type=bind,src={output_dir.resolve()},dst=/out",
            self.image,
            mode,
        ]
        raw = self._execute_container(command, name, timeout)
        if raw.timed_out:
            return ExecutionResult(
                status="timed_out",
                exit_code=None,
                duration_seconds=raw.duration_seconds,
                stdout=raw.stdout,
                stderr=raw.stderr,
                timed_out=True,
            )
        if raw.exit_code is None:
            return ExecutionResult(
                status="infrastructure_error",
                exit_code=None,
                duration_seconds=raw.duration_seconds,
                stdout=raw.stdout,
                stderr=raw.stderr,
            )
        if raw.exit_code == 0:
            status = "survived"
        elif raw.exit_code == 1:
            status = "killed"
        else:
            status = "broken"
        return ExecutionResult(
            status=status,
            exit_code=raw.exit_code,
            duration_seconds=raw.duration_seconds,
            stdout=raw.stdout,
            stderr=raw.stderr,
            failing_tests=_failing_tests(output_dir / "junit.xml"),
        )

    @staticmethod
    def _container_command(
        *, name: str, cpus: int, memory: str, pids: int
    ) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
            "--name",
            name,
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--pids-limit",
            str(pids),
            "--memory",
            memory,
            "--cpus",
            str(cpus),
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
        ]

    @staticmethod
    def _execute_container(
        command: list[str], name: str, timeout: float
    ) -> _ContainerRun:
        started = time.monotonic()
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            return _ContainerRun(
                exit_code=None,
                duration_seconds=time.monotonic() - started,
                stdout="",
                stderr=str(exc),
            )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            subprocess.run(
                ["docker", "stop", "--time", "1", name],
                capture_output=True,
                text=True,
                check=False,
            )
            subprocess.run(
                ["docker", "kill", name],
                capture_output=True,
                text=True,
                check=False,
            )
            stdout, stderr = process.communicate()
            return _ContainerRun(
                exit_code=None,
                duration_seconds=time.monotonic() - started,
                stdout=stdout,
                stderr=stderr,
                timed_out=True,
            )
        return _ContainerRun(
            exit_code=process.returncode,
            duration_seconds=time.monotonic() - started,
            stdout=stdout,
            stderr=stderr,
        )

    @staticmethod
    def _pythonpath(source_tree: Path) -> str:
        """Return supported import roots using their in-container locations.

        We always include the repository root.  In addition, an ``__init__.py``
        package whose parent is not itself a package is a top-level package, so
        its parent is an import root.  This covers conventional root packages,
        ``src/`` layouts, and a package placed in a project subdirectory without
        executing student installation metadata.
        """
        return ":".join(
            "/workspace" if root == "." else f"/workspace/{root}"
            for root in DockerSandbox.import_roots(source_tree)
        )

    @staticmethod
    def import_roots(source_tree: Path) -> tuple[str, ...]:
        """Return repository-relative import roots for isolated mutant trees."""
        roots = ["."]
        source_layout = source_tree / "src"
        if source_layout.is_dir() and any(source_layout.rglob("*.py")):
            roots.append("src")

        for init_file in sorted(source_tree.rglob("__init__.py")):
            package_dir = init_file.parent
            if (package_dir.parent / "__init__.py").exists():
                continue
            relative_root = package_dir.parent.relative_to(source_tree).as_posix()
            if relative_root not in roots:
                roots.append(relative_root)
        return tuple(roots)


def _failing_tests(junit_path: Path) -> tuple[str, ...]:
    if not junit_path.exists():
        return ()
    try:
        root = ET.parse(junit_path).getroot()
    except ET.ParseError:
        return ()
    failed: list[str] = []
    for case in root.iter("testcase"):
        if case.find("failure") is not None or case.find("error") is not None:
            classname = case.attrib.get("classname", "")
            name = case.attrib.get("name", "")
            failed.append("::".join(part for part in (classname, name) if part))
    return tuple(failed)
