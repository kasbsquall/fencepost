import gradebook.analytics


def test_letter_grade_assigns_b_at_inclusive_lower_boundary():
    assert gradebook.analytics.letter_grade(80) == "B"