import pytest

from gradebook.analytics import letter_grade


def test_letter_grade_assigns_b_at_exactly_80():
    assert letter_grade(80) == 'B'