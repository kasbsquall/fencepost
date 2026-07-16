import pytest

from gradebook.analytics import letter_grade


def test_letter_grade_includes_80_in_b_range():
    assert letter_grade(80) == "B"