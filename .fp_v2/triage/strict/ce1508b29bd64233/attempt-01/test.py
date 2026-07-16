import gradebook.analytics as analytics


def test_letter_grade_accepts_exact_b_lower_boundary():
    assert analytics.letter_grade(80) == 'B'