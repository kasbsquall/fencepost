from __future__ import annotations

from fencepost.models import (
    GeneratedAdversarialTest,
    GeneratedProbeGrade,
    GeneratedProbeQuestion,
)


class FixtureAdversarialTestGenerator:
    """Hermetic generator whose tests are still classified only by execution."""

    def __init__(self) -> None:
        self.keys: list[tuple[str, str, str, str, int]] = []

    def generate(self, request):
        candidate = request.mutant.candidate
        key = (
            candidate.path,
            candidate.kind,
            candidate.source_segment.strip(),
            candidate.after,
            request.attempt,
        )
        self.keys.append(key)
        semantic_key = key[:4]
        clamp_compare_keys = {
            (
                "gradebook/analytics.py",
                "compare",
                "p < 0",
                "LtE",
            ),
            (
                "gradebook/analytics.py",
                "compare",
                "p > 100",
                "GtE",
            ),
        }
        arithmetic_key = (
            "gradebook/analytics.py",
            "arithmetic",
            "len(ordered) * p / 100",
            "FloorDiv",
        )
        boundaries = {
            (
                "gradebook/analytics.py",
                "compare",
                f"score >= {score}",
                "Gt",
            ): score
            for score in (90, 80, 70, 60)
        }
        if semantic_key in clamp_compare_keys:
            if semantic_key[2] == "p < 0":
                source = (
                    "from gradebook.analytics import clamp_percent\n\n"
                    "def test_lower_boundary_preserves_negative_zero():\n"
                    "    assert str(clamp_percent(-0.0)) == '-0.0'\n"
                )
                behavior = "clamp_percent preserves plain negative zero"
            else:
                source = (
                    "from gradebook.analytics import clamp_percent\n\n"
                    "def test_upper_boundary_preserves_float_representation():\n"
                    "    assert str(clamp_percent(100.0)) == '100.0'\n"
                )
                behavior = "clamp_percent preserves plain upper-boundary float"
        elif semantic_key == arithmetic_key and request.mode == "STRICT":
            source = (
                "from gradebook.analytics import percentile\n\n"
                "class DivergentDivision:\n"
                "    def __lt__(self, other):\n"
                "        return False\n"
                "    def __gt__(self, other):\n"
                "        return False\n"
                "    def __rmul__(self, other):\n"
                "        return self\n"
                "    def __truediv__(self, other):\n"
                "        return 1\n"
                "    def __floordiv__(self, other):\n"
                "        return 0\n\n"
                "def test_custom_division_protocol():\n"
                "    assert percentile([10, 20], DivergentDivision()) == 20\n"
            )
            behavior = "custom true-division versus floor-division protocol"
        elif semantic_key == arithmetic_key and request.attempt == 1:
            source = (
                "import gradebook.analytics as analytics\n\n"
                "def test_percentile_without_its_clamp(monkeypatch):\n"
                "    monkeypatch.setattr(analytics, 'clamp_percent', float)\n"
                "    assert analytics.percentile([10, 20, 30, 40], -12.5) == 10\n"
            )
            behavior = "intentionally invalid attempt that replaces the program clamp"
        elif semantic_key == arithmetic_key:
            source = (
                "from gradebook.analytics import percentile\n\n"
                "def test_plain_percentile_index():\n"
                "    assert percentile([10, 20, 30], 50) == 20\n"
            )
            behavior = "plain numeric percentile index"
        elif semantic_key in boundaries:
            score = boundaries[semantic_key]
            expected = {90: "A", 80: "B", 70: "C", 60: "D"}[score]
            source = (
                "from gradebook.analytics import letter_grade\n\n"
                f"def test_letter_grade_boundary_{score}():\n"
                f"    assert letter_grade({score}) == {expected!r}\n"
            )
            behavior = f"letter_grade exact {score} boundary"
        elif (
            semantic_key[0] == "gradebook/analytics.py"
            and semantic_key[1] == "numeric_boundary"
            and semantic_key[2] in {"90", "80", "70", "60"}
        ):
            threshold = int(semantic_key[2])
            replacement = int(semantic_key[3])
            if replacement < threshold:
                score = threshold - 1
                expected = {90: "B", 80: "C", 70: "D", 60: "F"}[threshold]
            else:
                score = threshold
                expected = {90: "A", 80: "B", 70: "C", 60: "D"}[threshold]
            source = (
                "from gradebook.analytics import letter_grade\n\n"
                f"def test_letter_grade_numeric_boundary_{threshold}_{replacement}():\n"
                f"    assert letter_grade({score}) == {expected!r}\n"
            )
            behavior = f"letter_grade threshold literal {threshold} -> {replacement}"
        elif semantic_key == (
            "gradebook/analytics.py",
            "compare",
            "k >= len(ordered)",
            "Gt",
        ):
            source = (
                "from gradebook.analytics import percentile\n\n"
                "def test_percentile_one_hundred_returns_maximum():\n"
                "    assert percentile([10, 20, 30], 100) == 30\n"
            )
            behavior = "percentile at the upper endpoint"
        elif semantic_key == (
            "gradebook/analytics.py",
            "numeric_boundary",
            "0",
            "-1",
        ):
            source = (
                "from gradebook.analytics import clamp_percent\n\n"
                "def test_clamp_percent_clamps_negative_one():\n"
                "    assert clamp_percent(-1) == 0\n"
            )
            behavior = "clamp_percent lower comparison literal shifted down"
        elif semantic_key == (
            "gradebook/analytics.py",
            "numeric_boundary",
            "0",
            "1",
        ):
            source = (
                "from gradebook.analytics import clamp_percent\n\n"
                "def test_clamp_percent_preserves_positive_fraction():\n"
                "    assert clamp_percent(0.5) == 0.5\n"
            )
            behavior = "clamp_percent lower comparison literal shifted up"
        elif semantic_key == (
            "gradebook/analytics.py",
            "numeric_boundary",
            "100",
            "99",
        ):
            # This semantic key occurs once in clamp_percent and once in
            # percentile. Both assertions pass on the original and the relevant
            # assertion kills either mutant, without relying on an AST id.
            source = (
                "from gradebook.analytics import clamp_percent, percentile\n\n"
                "def test_upper_numeric_boundaries():\n"
                "    assert clamp_percent(99.5) == 99.5\n"
                "    assert percentile([30, 10, 20], 66) == 20\n"
            )
            behavior = "upper clamp and percentile denominator boundaries"
        elif semantic_key == (
            "gradebook/analytics.py",
            "numeric_boundary",
            "100",
            "101",
        ):
            source = (
                "from gradebook.analytics import clamp_percent\n\n"
                "def test_clamp_percent_clamps_one_hundred_one():\n"
                "    assert clamp_percent(101) == 100\n"
            )
            behavior = "clamp_percent upper comparison literal shifted up"
        else:
            function_name = request.qualified_function_name.split(".")[-1]
            test_name = "".join(
                character if character.isalnum() else "_"
                for character in candidate.id
            )
            source = (
                f"from {request.module_path} import {function_name}\n\n"
                f"def test_fixture_smoke_{test_name}_{request.attempt}():\n"
                f"    assert callable({function_name})\n"
            )
            behavior = "deterministic non-distinguishing fixture smoke test"
        return GeneratedAdversarialTest(
            source=source,
            targeted_behavior=behavior,
            provider="fixture-fake",
            model=None,
            response_id=None,
            generation_duration_seconds=0.0,
        )


class FixtureComprehensionProbeAgent:
    """Hermetic question/grade seam; evidence attachment remains engine-owned."""

    model = None

    def __init__(self) -> None:
        self.question_requests = []
        self.grade_requests = []

    def generate_question(self, request):
        self.question_requests.append(request)
        first = request.grounding.authored_lines[0]
        mutation = (
            f"Consider changing `{request.mutation.original_segment}` to "
            f"`{request.mutation.mutated_segment}`."
        )
        question = (
            f"In commit {first.commit[:7]} on {first.author_date}, you wrote "
            f"line {first.line} of {request.grounding.path}.\n\n"
            f"{mutation}\n\n"
            "What observable behavior changes, and why?"
        )
        return GeneratedProbeQuestion(
            question_text=question,
            mutation_description=mutation,
            provider="fixture-fake",
            model=None,
            response_id=None,
            generation_duration_seconds=0.0,
        )

    def grade_answer(self, request):
        self.grade_requests.append(request)
        failure = request.evidence.failing_assertion
        normalized = request.answer.strip().casefold()
        verdict = (
            "INSUFFICIENT"
            if normalized in {"", "i don't know", "insufficient"}
            else "PARTIAL"
        )
        return GeneratedProbeGrade(
            verdict=verdict,
            feedback=(
                "Review the answer against the execution-grounded boundary behavior."
            ),
            evidence_explanation=(
                f"The mutant failed {failure.nodeid}: {failure.message}"
            ),
            provider="fixture-fake",
            model=None,
            response_id=None,
            generation_duration_seconds=0.0,
        )
