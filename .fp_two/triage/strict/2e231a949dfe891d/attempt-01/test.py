import pytest

from gradebook.analytics import letter_grade


def test_score_89_is_b_not_a():
    assert letter_grade(89) == "B"