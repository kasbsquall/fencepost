import pytest
import gradebook.analytics


def test_letter_grade_59_is_failing():
    assert gradebook.analytics.letter_grade(59) == "F"