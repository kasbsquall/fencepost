import gradebook.analytics


def test_letter_grade_awards_d_at_inclusive_lower_boundary():
    assert gradebook.analytics.letter_grade(60) == "D"