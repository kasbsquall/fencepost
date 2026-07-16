import gradebook.analytics


def test_letter_grade_assigns_c_at_inclusive_lower_boundary():
    assert gradebook.analytics.letter_grade(70) == "C"