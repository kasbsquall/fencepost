import pytest

from gradebook.analytics import letter_grade


def test_letter_grade_assigns_c_at_inclusive_70_boundary():
    assert letter_grade(70) == "C"