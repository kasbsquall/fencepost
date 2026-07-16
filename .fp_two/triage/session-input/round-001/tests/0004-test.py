import pytest

from gradebook.analytics import letter_grade


def test_79_is_a_c_grade():
    assert letter_grade(79) == "C"