import gradebook.analytics as analytics


def test_letter_grade_assigns_b_at_inclusive_lower_boundary():
    assert analytics.letter_grade(80) == "B"