from __future__ import annotations

import json
from types import SimpleNamespace

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
