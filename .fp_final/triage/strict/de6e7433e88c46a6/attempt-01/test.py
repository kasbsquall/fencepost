import gradebook.analytics as analytics


def test_letter_grade_79_is_c():
    assert analytics.letter_grade(79) == "C"