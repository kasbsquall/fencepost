from __future__ import annotations

import json
from types import SimpleNamespace

from fencepost.models import TriageJob
from fencepost.sandbox import DockerSandbox


def test_batch_uses_one_hardened_container_for_all_mutants(tmp_path, monkeypatch) -> None:
    baseline = tmp_path / "baseline"
    batch_input = tmp_path / "input"
    output = tmp_path / "output"
    baseline.mkdir()
    batch_input.mkdir()
    output.mkdir()
    calls: list[list[str]] = []

    def fake_execute(command, name, timeout):
        calls.append(command)
        (output / "batch-results.json").write_text(
            json.dumps(
                {
                    "results": {
                        "m1": {
                            "status": "survived",
                            "exit_code": 0,
                            "duration_seconds": 0.25,
                            "stdout": "",
                            "stderr": "",
                            "timed_out": False,
                            "failing_tests": [],
                        }
                    },
                    "aborted_all_broken": False,
                    "duration_seconds": 1.0,
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(
            exit_code=0,
            duration_seconds=1.0,
            stdout="",
            stderr="",
            timed_out=False,
        )

    monkeypatch.setattr(DockerSandbox, "_execute_container", staticmethod(fake_execute))
    sandbox = DockerSandbox("fencepost-runner:test", tmp_path, build_image=False)

    result = sandbox.batch(
        baseline,
        batch_input,
        output,
        mutant_count=40,
        per_mutant_timeout=5.0,
        workers=4,
    )

    assert len(calls) == 1
    command = calls[0]
    assert "fencepost-runner:test" in command
    assert command[-1] == "batch"
    assert "/work:rw,nosuid,size=512m" in command
    assert f"type=bind,src={baseline.resolve()},dst=/baseline,readonly" in command
    assert f"type=bind,src={batch_input.resolve()},dst=/input,readonly" in command
    assert result.results["m1"].status == "survived"


def test_triage_reuses_one_persistent_hardened_container_for_retry_rounds(
    tmp_path, monkeypatch
) -> None:
    baseline = tmp_path / "baseline"
    triage_input = tmp_path / "triage-input"
    output = tmp_path / "triage-output"
    baseline.mkdir()
    run_calls: list[list[str]] = []
    exec_calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        run_calls.append(command)
        return SimpleNamespace(returncode=0, stdout="container-id\n", stderr="")

    def fake_execute(command, name, timeout):
        exec_calls.append(command)
        result_name = command[-1].removeprefix("/out/")
        output.mkdir(parents=True, exist_ok=True)
        (output / result_name).write_text(
            json.dumps(
                {
                    "results": {
                        command[-2].split("/")[-2] + "-job": {
                            "outcome": "NOT_DISTINGUISHED",
                            "original": {
                                "status": "passed",
                                "exit_code": 0,
                                "duration_seconds": 0.01,
                                "stdout": "",
                                "stderr": "",
                                "tests_collected": 1,
                                "tests_skipped": 0,
                                "failure": None,
                            },
                            "mutant": {
                                "status": "passed",
                                "exit_code": 0,
                                "duration_seconds": 0.01,
                                "stdout": "",
                                "stderr": "",
                                "tests_collected": 1,
                                "tests_skipped": 0,
                                "failure": None,
                            },
                        }
                    },
                    "infrastructure_errors": [],
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(
            exit_code=0,
            duration_seconds=0.1,
            stdout="",
            stderr="",
            timed_out=False,
        )

    monkeypatch.setattr("fencepost.sandbox.subprocess.run", fake_run)
    monkeypatch.setattr(DockerSandbox, "_execute_container", staticmethod(fake_execute))
    sandbox = DockerSandbox("fencepost-runner:test", tmp_path, build_image=False)
    session = sandbox.triage_session(
        baseline,
        triage_input,
        output,
        import_roots=(".",),
        workers=2,
        per_test_timeout=5.0,
    )

    with session:
        for round_id in (1, 2):
            round_name = f"round-{round_id:03d}"
            results = session.run_round(
                round_id,
                [
                    TriageJob(
                        id=f"{round_name}-job",
                        mutant_path="pkg/module.py",
                        mutant_source="value = 2\n",
                        test_source="def test_value():\n    assert True\n",
                        attempt=round_id,
                    )
                ],
            )
            assert results[f"{round_name}-job"].outcome == "NOT_DISTINGUISHED"

    starts = [call for call in run_calls if call[:2] == ["docker", "run"]]
    stops = [call for call in run_calls if call[:2] == ["docker", "stop"]]
    assert len(starts) == 1
    assert len(stops) == 1
    assert len(exec_calls) == 2
    start = starts[0]
    assert "--network" in start and "none" in start
    assert "--read-only" in start
    assert "/work:rw,nosuid,size=512m" in start
    assert f"type=bind,src={baseline.resolve()},dst=/baseline,readonly" in start
    assert f"type=bind,src={triage_input.resolve()},dst=/input,readonly" in start
