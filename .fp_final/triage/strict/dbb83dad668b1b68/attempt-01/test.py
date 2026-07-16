import pytest

from gradebook.analytics import letter_grade


def test_score_69_is_a_d():
    assert letter_grade(69) == "D"