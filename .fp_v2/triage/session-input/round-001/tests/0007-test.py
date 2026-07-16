import pytest

from gradebook.analytics import letter_grade


def test_69_is_a_d_not_a_c():
    assert letter_grade(69) == "D"