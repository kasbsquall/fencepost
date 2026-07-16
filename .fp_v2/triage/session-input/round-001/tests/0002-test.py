import gradebook.analytics as analytics


def test_letter_grade_awards_a_at_exact_lower_boundary():
    assert analytics.letter_grade(90) == "A"