import gradebook.analytics


def test_letter_grade_includes_80_in_b_range():
    assert gradebook.analytics.letter_grade(80) == "B"