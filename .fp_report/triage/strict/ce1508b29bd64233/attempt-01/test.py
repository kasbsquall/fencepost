import gradebook.analytics as analytics


def test_letter_grade_includes_80_in_b_range():
    assert analytics.letter_grade(80) == "B"