"""Execute a mutation batch inside one long-lived Docker container."""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
import xml.etree.ElementTree as ET


BASELINE = Path("/baseline")
INPUT = Path("/input")
WORK = Path("/work/jobs")


def _command(
    arguments: list[str], cwd: Path, environment: dict[str, str], deadline: float
) -> tuple[int | None, str, str, bool]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None, "", "", True
    process = subprocess.Popen(
        arguments,
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=remaining)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        return None, stdout, stderr, True
    return process.returncode, stdout, stderr, False


def _failing_tests(junit_path: Path) -> list[str]:
    if not junit_path.exists():
        return []
    try:
        root = ET.parse(junit_path).getroot()
    except ET.ParseError:
        return []
    failed: list[str] = []
    for case in root.iter("testcase"):
        if case.find("failure") is not None or case.find("error") is not None:
            classname = case.attrib.get("classname", "")
            name = case.attrib.get("name", "")
            failed.append("::".join(part for part in (classname, name) if part))
    return failed


def _result(
    *,
    status: str,
    exit_code: int | None,
    started: float,
    stdout: list[str],
    stderr: list[str],
    timed_out: bool = False,
    failing_tests: list[str] | None = None,
) -> dict[str, object]:
    return {
        "status": status,
        "exit_code": exit_code,
        "duration_seconds": time.monotonic() - started,
        "stdout": "\n".join(part for part in stdout if part),
        "stderr": "\n".join(part for part in stderr if part),
        "timed_out": timed_out,
        "failing_tests": failing_tests or [],
    }


def _safe_relative_path(value: str) -> PurePosixPath:
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError(f"unsafe mutation path: {value!r}")
    return relative


def _run_mutant(
    index: int,
    mutant: dict[str, str],
    import_roots: list[str],
    timeout_seconds: float,
) -> tuple[int, str, dict[str, object]]:
    mutant_id = mutant["id"]
    started = time.monotonic()
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    job_container = Path(tempfile.mkdtemp(prefix=f"{index:04d}-", dir=WORK))
    tree = job_container / "tree"
    try:
        shutil.copytree(BASELINE, tree, symlinks=True)
        relative_target = _safe_relative_path(mutant["path"])
        target = tree.joinpath(*relative_target.parts)
        if target.is_symlink() or tree.resolve() not in target.resolve().parents:
            raise ValueError(f"mutation target escapes isolated tree: {mutant['path']!r}")
        source_file = INPUT / "sources" / mutant["source_file"]
        target.write_text(source_file.read_text(encoding="utf-8"), encoding="utf-8")

        job_tmp = job_container / "tmp"
        job_tmp.mkdir()
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            str(tree if root == "." else tree / root) for root in import_roots
        )
        environment["PYTHONPYCACHEPREFIX"] = str(job_container / "pycache")
        environment["TMPDIR"] = str(job_tmp)
        deadline = started + timeout_seconds

        phases = (
            ([sys.executable, "-m", "compileall", "-q", "."], 10, "broken"),
            (
                [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
                11,
                "broken",
            ),
        )
        for command, failure_code, status in phases:
            exit_code, stdout, stderr, timed_out = _command(
                command, tree, environment, deadline
            )
            stdout_parts.append(stdout)
            stderr_parts.append(stderr)
            if timed_out:
                return index, mutant_id, _result(
                    status="timed_out",
                    exit_code=None,
                    started=started,
                    stdout=stdout_parts,
                    stderr=stderr_parts,
                    timed_out=True,
                )
            if exit_code != 0:
                return index, mutant_id, _result(
                    status=status,
                    exit_code=failure_code,
                    started=started,
                    stdout=stdout_parts,
                    stderr=stderr_parts,
                )

        junit_path = job_container / "junit.xml"
        exit_code, stdout, stderr, timed_out = _command(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                f"--junitxml={junit_path}",
            ],
            tree,
            environment,
            deadline,
        )
        stdout_parts.append(stdout)
        stderr_parts.append(stderr)
        if timed_out:
            result = _result(
                status="timed_out",
                exit_code=None,
                started=started,
                stdout=stdout_parts,
                stderr=stderr_parts,
                timed_out=True,
            )
        else:
            status = "survived" if exit_code == 0 else "killed" if exit_code == 1 else "broken"
            result = _result(
                status=status,
                exit_code=exit_code,
                started=started,
                stdout=stdout_parts,
                stderr=stderr_parts,
                failing_tests=_failing_tests(junit_path),
            )
        return index, mutant_id, result
    except Exception as exc:
        stderr_parts.append(f"batch driver failed: {type(exc).__name__}: {exc}")
        return index, mutant_id, _result(
            status="infrastructure_error",
            exit_code=None,
            started=started,
            stdout=stdout_parts,
            stderr=stderr_parts,
        )
    finally:
        shutil.rmtree(job_container, ignore_errors=True)


def _run_batch(manifest: dict[str, object]) -> tuple[dict[str, dict[str, object]], bool]:
    mutants = manifest["mutants"]
    if not isinstance(mutants, list):
        raise ValueError("manifest mutants must be a list")
    workers = int(manifest["workers"])
    timeout_seconds = float(manifest["timeout_seconds"])
    import_roots = [str(root) for root in manifest["import_roots"]]
    WORK.mkdir(parents=True, exist_ok=True)

    results_by_index: dict[int, tuple[str, dict[str, object]]] = {}
    pending: dict[Future, int] = {}
    next_index = 0
    aborted = False

    with ThreadPoolExecutor(max_workers=workers) as pool:
        while next_index < len(mutants) and len(pending) < workers:
            future = pool.submit(
                _run_mutant,
                next_index,
                mutants[next_index],
                import_roots,
                timeout_seconds,
            )
            pending[future] = next_index
            next_index += 1

        while pending:
            completed, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                pending.pop(future)
                index, mutant_id, result = future.result()
                results_by_index[index] = (mutant_id, result)

            probe_size = min(5, len(mutants))
            if all(index in results_by_index for index in range(probe_size)) and all(
                results_by_index[index][1]["status"] == "broken"
                for index in range(probe_size)
            ):
                aborted = True
                for future in pending:
                    future.cancel()
                break

            while next_index < len(mutants) and len(pending) < workers:
                future = pool.submit(
                    _run_mutant,
                    next_index,
                    mutants[next_index],
                    import_roots,
                    timeout_seconds,
                )
                pending[future] = next_index
                next_index += 1


    ordered = {
        mutant_id: result
        for _, (mutant_id, result) in sorted(results_by_index.items())
    }
    return ordered, aborted


def main() -> int:
    manifest_path = Path(sys.argv[1])
    result_path = Path(sys.argv[2])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    started = time.monotonic()
    results, aborted = _run_batch(manifest)
    payload = {
        "results": results,
        "aborted_all_broken": aborted,
        "duration_seconds": time.monotonic() - started,
    }
    temporary = result_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(result_path)
    return 12 if aborted else 0


if __name__ == "__main__":
    raise SystemExit(main())
