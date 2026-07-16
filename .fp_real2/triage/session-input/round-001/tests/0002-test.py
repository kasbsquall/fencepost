"""Mutation-killing tests for gradebook.analytics.letter_grade."""

from gradebook.analytics import letter_grade


def test_letter_grade_includes_90_in_a_range():
    assert letter_grade(90) == "A"