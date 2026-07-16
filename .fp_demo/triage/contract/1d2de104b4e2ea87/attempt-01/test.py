import gradebook.analytics as analytics


def test_letter_grade_assigns_a_at_inclusive_lower_boundary():
    assert analytics.letter_grade(90) == "A"