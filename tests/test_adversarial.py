from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from fencepost.adversarial import (
    AdversarialGeneratorError,
    CodexCliAdversarialTestGenerator,
    OpenAIAdversarialTestGenerator,
)
from fencepost.models import (
    AdversarialTestRequest,
    ExecutionResult,
    MutantResult,
    MutationCandidate,
    PathStep,
    SourceSpan,
)


def _request() -> AdversarialTestRequest:
    mutant = MutantResult(
        candidate=MutationCandidate(
            id="mutant-1",
            path="pkg/analytics.py",
            anchor=SourceSpan(2, 7, 2, 17),
            ast_path=(PathStep("body", 0), PathStep("body", 0)),
            kind="compare",
            before="GtE",
            after="Gt",
            source_segment="score >= 90",
        ),
        generated_anchor=SourceSpan(2, 7, 2, 16),
        execution=ExecutionResult("survived", 0, 0.1, "", ""),
    )
    return AdversarialTestRequest(
        mutant=mutant,
        attempt=1,
        valid_attempts_completed=0,
        module_path="pkg.analytics",
        qualified_function_name="letter_grade",
        original_function="def letter_grade(score):\n    return score >= 90",
        mutated_function="def letter_grade(score):\n    return score > 90",
        unified_diff="- score >= 90\n+ score > 90",
    )


def test_openai_generator_uses_configured_model_and_structured_response() -> None:
    calls: list[dict[str, object]] = []

    class Responses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                id="resp_fixture",
                model="available-gpt-5.6",
                output_text=json.dumps(
                    {
                        "source": "def test_boundary():\n    assert True\n",
                        "targeted_behavior": "exact boundary",
                    }
                ),
                usage=SimpleNamespace(input_tokens=123, output_tokens=45),
            )

    client = SimpleNamespace(responses=Responses())
    generator = OpenAIAdversarialTestGenerator(
        model="available-gpt-5.6", client=client
    )

    generated = generator.generate(_request())

    assert len(calls) == 1
    call = calls[0]
    assert call["model"] == "available-gpt-5.6"
    assert call["store"] is False
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True
    prompt = json.loads(call["input"])
    assert prompt["original_function"].endswith("score >= 90")
    assert prompt["mutated_function"].endswith("score > 90")
    assert prompt["unified_diff"] == "- score >= 90\n+ score > 90"
    assert generated.model == "available-gpt-5.6"
    assert generated.response_id == "resp_fixture"
    assert generated.input_tokens == 123
    assert generated.source.startswith("def test_boundary")


def test_codex_cli_generator_builds_isolated_structured_command_and_strips_fence(
    tmp_path, monkeypatch
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []
    schemas: list[dict[str, object]] = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        schema_path = command[command.index("--output-schema") + 1]
        schemas.append(json.loads(open(schema_path, encoding="utf-8").read()))
        events = [
            {"type": "thread.started", "thread_id": "thread_fixture"},
            {
                "type": "item.completed",
                "item": {
                    "id": "item_1",
                    "type": "agent_message",
                    "text": json.dumps(
                        {
                            "test_source": (
                                "```python\n"
                                "def test_boundary():\n"
                                "    assert True\n"
                                "```"
                            ),
                            "targeted_behavior": "exact boundary",
                        }
                    ),
                },
            },
            {
                "type": "turn.completed",
                "usage": {"input_tokens": 321, "output_tokens": 54},
            },
        ]
        return SimpleNamespace(
            returncode=0,
            stdout="\n".join(json.dumps(event) for event in events),
            stderr="",
        )

    monkeypatch.setattr("fencepost.adversarial.subprocess.run", fake_run)
    generator = CodexCliAdversarialTestGenerator(
        model="gpt-5.6-terra",
        executable="codex-test",
        timeout_seconds=123.0,
        temporary_root=tmp_path,
    )

    generated = generator.generate(_request())

    assert len(calls) == 1
    command, options = calls[0]
    assert command[:4] == ["codex-test", "exec", "-m", "gpt-5.6-terra"]
    assert ["-c", "mcp_servers={}"] == command[4:6]
    assert ["-c", 'sandbox_mode="read-only"'] == command[6:8]
    assert "--output-schema" in command
    assert "--json" in command
    assert "--output-last-message" in command
    assert "--skip-git-repo-check" in command
    assert command[-1] == "-"
    assert schemas[0]["required"] == ["test_source", "targeted_behavior"]
    assert options["cwd"] != tmp_path
    assert options["cwd"].parent == tmp_path
    assert options["input"].find("score >= 90") >= 0
    assert options["capture_output"] is True
    assert options["text"] is True
    assert options["check"] is False
    assert options["timeout"] == 123.0
    assert generated.provider == "codex-cli"
    assert generated.model == "gpt-5.6-terra"
    assert generated.response_id == "thread_fixture"
    assert generated.input_tokens == 321
    assert generated.output_tokens == 54
    assert generated.source == "def test_boundary():\n    assert True"


def test_codex_cli_nonzero_exit_is_generator_failure(tmp_path, monkeypatch) -> None:
    def fake_run(command, **kwargs):
        return SimpleNamespace(
            returncode=17,
            stdout="",
            stderr="authentication unavailable",
        )

    monkeypatch.setattr("fencepost.adversarial.subprocess.run", fake_run)
    generator = CodexCliAdversarialTestGenerator(
        model="gpt-5.6-sol",
        executable="codex-test",
        temporary_root=tmp_path,
    )

    with pytest.raises(AdversarialGeneratorError, match="exited 17"):
        generator.generate(_request())
