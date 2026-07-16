import pytest

from gradebook.analytics import letter_grade


def test_score_just_below_d_threshold_is_f():
    assert letter_grade(59) == "F"