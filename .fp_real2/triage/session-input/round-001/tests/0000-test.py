import pytest

from gradebook.analytics import letter_grade


def test_letter_grade_90_is_an_a():
    assert letter_grade(90) == "A"