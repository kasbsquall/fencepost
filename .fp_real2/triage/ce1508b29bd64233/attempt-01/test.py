import pytest

from gradebook.analytics import letter_grade


def test_b_grade_includes_exactly_80():
    assert letter_grade(80) == "B"