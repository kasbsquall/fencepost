from __future__ import annotations

import json
from types import SimpleNamespace

from fencepost.adversarial import OpenAIAdversarialTestGenerator
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
