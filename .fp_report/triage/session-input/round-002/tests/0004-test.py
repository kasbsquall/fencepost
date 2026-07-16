import pytest
from gradebook.analytics import letter_grade


def test_letter_grade_79_is_c():
    assert letter_grade(79) == "C"