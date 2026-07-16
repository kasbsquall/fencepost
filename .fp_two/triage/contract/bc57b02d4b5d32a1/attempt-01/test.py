import gradebook.analytics


def test_letter_grade_returns_b_at_80():
    assert gradebook.analytics.letter_grade(80) == "B"