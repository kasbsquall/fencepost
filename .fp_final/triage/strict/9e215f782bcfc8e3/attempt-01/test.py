import gradebook.analytics as analytics


def test_letter_grade_includes_60_in_d_range():
    assert analytics.letter_grade(60) == "D"