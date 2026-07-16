import gradebook.analytics as analytics


def test_letter_grade_includes_70_in_c_range():
    assert analytics.letter_grade(70) == "C"