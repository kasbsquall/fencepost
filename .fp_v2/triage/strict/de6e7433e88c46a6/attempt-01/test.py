import pytest

from gradebook.analytics import letter_grade


def test_score_79_is_a_c_not_a_b():
    assert letter_grade(79) == "C"