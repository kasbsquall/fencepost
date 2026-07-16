import gradebook.analytics


def test_letter_grade_assigns_a_at_inclusive_lower_boundary():
    assert gradebook.analytics.letter_grade(90) == "A"