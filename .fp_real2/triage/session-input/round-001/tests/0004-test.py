import pytest

from gradebook.analytics import letter_grade


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (79, "C"),
        (80, "B"),
    ],
)
def test_b_grade_starts_at_80(score, expected):
    assert letter_grade(score) == expected