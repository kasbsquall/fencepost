import pytest

from gradebook.analytics import letter_grade


def test_letter_grade_69_is_d_not_c():
    assert letter_grade(69) == "D"