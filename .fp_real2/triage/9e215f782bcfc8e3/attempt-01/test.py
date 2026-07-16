import pytest

from gradebook.analytics import letter_grade


def test_letter_grade_assigns_d_at_inclusive_lower_boundary():
    assert letter_grade(60) == "D"