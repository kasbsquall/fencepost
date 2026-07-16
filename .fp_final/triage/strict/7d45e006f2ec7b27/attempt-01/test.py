import gradebook.analytics as analytics


def test_letter_grade_accepts_60_as_d():
    assert analytics.letter_grade(60) == "D"