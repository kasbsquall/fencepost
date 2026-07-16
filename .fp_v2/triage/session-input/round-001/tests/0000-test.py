import pytest

from gradebook.analytics import letter_grade


def test_letter_grade_assigns_a_at_exactly_90():
    assert letter_grade(90) == "A"