import gradebook.analytics


def test_letter_grade_includes_ninety_in_a_range():
    assert gradebook.analytics.letter_grade(90) == "A"