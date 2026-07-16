import pytest
import gradebook.analytics


def test_letter_grade_69_is_d():
    assert gradebook.analytics.letter_grade(69) == "D"