import pytest

from gradebook.analytics import letter_grade


def test_letter_grade_assigns_d_at_exactly_sixty():
    assert letter_grade(60) == "D"