import pytest

from gradebook.analytics import letter_grade


def test_letter_grade_80_is_b():
    assert letter_grade(80) == "B"