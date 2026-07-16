from __future__ import annotations

from fencepost.models import GeneratedAdversarialTest


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
        boundaries = {
            (
                "gradebook/analytics.py",
                "compare",
                f"score >= {score}",
                "Gt",
            ): score
            for score in (90, 80, 70, 60)
        }
        if semantic_key in boundaries:
            score = boundaries[semantic_key]
            expected = {90: "A", 80: "B", 70: "C", 60: "D"}[score]
            source = (
                "from gradebook.analytics import letter_grade\n\n"
                f"def test_letter_grade_boundary_{score}():\n"
                f"    assert letter_grade({score}) == {expected!r}\n"
            )
            behavior = f"letter_grade exact {score} boundary"
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
        else:
            function_name = request.qualified_function_name.split(".")[-1]
            test_name = "".join(
                character if character.isalnum() else "_"
                for character in candidate.id
            )
            source = (
                "import importlib\n\n"
                f"def test_fixture_smoke_{test_name}_{request.attempt}():\n"
                f"    module = importlib.import_module({request.module_path!r})\n"
                f"    assert callable(getattr(module, {function_name!r}))\n"
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
