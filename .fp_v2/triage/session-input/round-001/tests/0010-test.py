import pytest

from gradebook.analytics import letter_grade


def test_score_59_is_failing_not_a_d():
    assert letter_grade(59) == "F"