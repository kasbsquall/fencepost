import gradebook.analytics


def test_letter_grade_includes_seventy_in_c_range():
    assert gradebook.analytics.letter_grade(70) == 'C'