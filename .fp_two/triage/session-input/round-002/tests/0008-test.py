import pytest
import gradebook.analytics


def test_letter_grade_assigns_c_at_lower_c_boundary():
    assert gradebook.analytics.letter_grade(70) == "C"