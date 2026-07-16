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


def _junit_details(junit_path: Path) -> tuple[int, int, dict[str, str] | None]:
    if not junit_path.exists():
        return 0, 0, None
    try:
        root = ET.parse(junit_path).getroot()
    except ET.ParseError:
        return 0, 0, None
    cases = list(root.iter("testcase"))
    skipped = sum(case.find("skipped") is not None for case in cases)
    for case in cases:
        for kind in ("failure", "error"):
            element = case.find(kind)
            if element is None:
                continue
            classname = case.attrib.get("classname", "")
            name = case.attrib.get("name", "")
            return len(cases), skipped, {
                "nodeid": "::".join(
                    part for part in (classname, name) if part
                ),
                "kind": kind,
                "message": element.attrib.get("message", "")[:2000],
                "detail": (element.text or "")[:8000],
            }
    return len(cases), skipped, None


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


def _test_execution(
    *,
    tree: Path,
    relative_test: Path,
    job_root: Path,
    import_roots: list[str],
    timeout_seconds: float,
    phase: str,
) -> dict[str, object]:
    started = time.monotonic()
    phase_root = job_root / phase
    phase_root.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        str(tree if root == "." else tree / root) for root in import_roots
    )
    environment["PYTHONPYCACHEPREFIX"] = str(phase_root / "pycache")
    environment["TMPDIR"] = str(phase_root / "tmp")
    (phase_root / "tmp").mkdir()
    junit_path = phase_root / "junit.xml"
    exit_code, stdout, stderr, timed_out = _command(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--rootdir={tree}",
            f"--junitxml={junit_path}",
            str(relative_test),
        ],
        tree,
        environment,
        started + timeout_seconds,
    )
    tests_collected, tests_skipped, failure = _junit_details(junit_path)
    if timed_out:
        status = "timed_out"
        failure = {
            "nodeid": str(relative_test),
            "kind": "timeout",
            "message": f"pytest exceeded {timeout_seconds:.1f}s",
            "detail": "The generated test passed on the original but did not terminate on the mutant."
            if phase == "mutant"
            else "The generated test did not terminate on the original code.",
        }
    elif exit_code == 0:
        status = "passed"
    else:
        status = "failed"
    return {
        "status": status,
        "exit_code": exit_code,
        "duration_seconds": time.monotonic() - started,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "tests_collected": tests_collected,
        "tests_skipped": tests_skipped,
        "failure": failure,
    }


def _run_triage_job(
    index: int,
    job: dict[str, object],
    round_input: Path,
    import_roots: list[str],
    timeout_seconds: float,
) -> tuple[int, str, dict[str, object], str | None]:
    job_id = str(job["id"])
    job_container = Path(tempfile.mkdtemp(prefix=f"triage-{index:04d}-", dir=WORK))
    try:
        original_tree = job_container / "original" / "tree"
        mutant_tree = job_container / "mutant" / "tree"
        shutil.copytree(BASELINE, original_tree, symlinks=True)
        shutil.copytree(BASELINE, mutant_tree, symlinks=True)

        relative_target = _safe_relative_path(str(job["path"]))
        target = mutant_tree.joinpath(*relative_target.parts)
        if target.is_symlink() or mutant_tree.resolve() not in target.resolve().parents:
            raise ValueError(f"mutation target escapes isolated tree: {job['path']!r}")
        mutant_source = round_input / "sources" / str(job["source_file"])
        target.write_text(mutant_source.read_text(encoding="utf-8"), encoding="utf-8")

        generated_dir_name = f".fencepost-generated-{index:04d}"
        relative_test = Path(generated_dir_name) / "test_adversarial.py"
        test_source = (round_input / "tests" / str(job["test_file"])).read_text(
            encoding="utf-8"
        )
        for tree in (original_tree, mutant_tree):
            generated_dir = tree / generated_dir_name
            if generated_dir.exists():
                raise ValueError(
                    f"reserved generated-test path already exists: {generated_dir_name}"
                )
            generated_dir.mkdir()
            (tree / relative_test).write_text(test_source, encoding="utf-8")

        original = _test_execution(
            tree=original_tree,
            relative_test=relative_test,
            job_root=job_container,
            import_roots=import_roots,
            timeout_seconds=timeout_seconds,
            phase="original",
        )
        original_executed = int(original["tests_collected"]) - int(
            original["tests_skipped"]
        )
        if original["status"] != "passed" or original_executed < 1:
            return index, job_id, {
                "outcome": "INVALID_ON_ORIGINAL",
                "original": original,
                "mutant": None,
            }, None

        mutant = _test_execution(
            tree=mutant_tree,
            relative_test=relative_test,
            job_root=job_container,
            import_roots=import_roots,
            timeout_seconds=timeout_seconds,
            phase="mutant",
        )
        if mutant["status"] == "passed":
            outcome = "NOT_DISTINGUISHED"
        elif mutant["status"] == "timed_out":
            outcome = "DISTINGUISHED"
        elif mutant["exit_code"] == 1 and mutant["failure"] is not None:
            outcome = "DISTINGUISHED"
        else:
            return index, job_id, {
                "outcome": "NOT_DISTINGUISHED",
                "original": original,
                "mutant": mutant,
            }, (
                f"mutant pytest produced a non-semantic failure for {job_id}: "
                f"exit={mutant['exit_code']} status={mutant['status']}"
            )
        return index, job_id, {
            "outcome": outcome,
            "original": original,
            "mutant": mutant,
        }, None
    except Exception as exc:
        return index, job_id, {
            "outcome": "NOT_DISTINGUISHED",
            "original": {
                "status": "infrastructure_error",
                "exit_code": None,
                "duration_seconds": 0.0,
                "stdout": "",
                "stderr": str(exc),
                "timed_out": False,
                "tests_collected": 0,
                "tests_skipped": 0,
                "failure": None,
            },
            "mutant": None,
        }, f"triage driver failed for {job_id}: {type(exc).__name__}: {exc}"
    finally:
        shutil.rmtree(job_container, ignore_errors=True)


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


def _run_triage_batch(
    manifest: dict[str, object], round_input: Path
) -> tuple[dict[str, dict[str, object]], list[str]]:
    jobs = manifest["jobs"]
    if not isinstance(jobs, list):
        raise ValueError("triage manifest jobs must be a list")
    workers = int(manifest["workers"])
    timeout_seconds = float(manifest["timeout_seconds"])
    import_roots = [str(root) for root in manifest["import_roots"]]
    WORK.mkdir(parents=True, exist_ok=True)

    completed: dict[int, tuple[str, dict[str, object], str | None]] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                _run_triage_job,
                index,
                job,
                round_input,
                import_roots,
                timeout_seconds,
            )
            for index, job in enumerate(jobs)
        ]
        for future in futures:
            index, job_id, result, error = future.result()
            completed[index] = (job_id, result, error)

    ordered = {
        job_id: result
        for _, (job_id, result, _) in sorted(completed.items())
    }
    errors = [
        error
        for _, (_, _, error) in sorted(completed.items())
        if error is not None
    ]
    return ordered, errors


def main() -> int:
    triage_mode = len(sys.argv) == 4 and sys.argv[1] == "triage"
    offset = 2 if triage_mode else 1
    manifest_path = Path(sys.argv[offset])
    result_path = Path(sys.argv[offset + 1])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    started = time.monotonic()
    if triage_mode:
        results, errors = _run_triage_batch(manifest, manifest_path.parent)
        payload = {
            "results": results,
            "infrastructure_errors": errors,
            "duration_seconds": time.monotonic() - started,
        }
    else:
        results, aborted = _run_batch(manifest)
        payload = {
            "results": results,
            "aborted_all_broken": aborted,
            "duration_seconds": time.monotonic() - started,
        }
    temporary = result_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(result_path)
    if triage_mode:
        return 13 if errors else 0
    return 12 if aborted else 0


if __name__ == "__main__":
    raise SystemExit(main())
