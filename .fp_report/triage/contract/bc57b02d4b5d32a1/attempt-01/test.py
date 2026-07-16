import gradebook.analytics


def test_letter_grade_includes_b_lower_boundary():
    assert gradebook.analytics.letter_grade(80) == "B"