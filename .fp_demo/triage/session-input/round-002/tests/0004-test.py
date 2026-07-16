import gradebook.analytics


def test_letter_grade_79_is_c():
    assert gradebook.analytics.letter_grade(79) == "C"