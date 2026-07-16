import gradebook.analytics as analytics


def test_letter_grade_assigns_d_at_exactly_sixty():
    assert analytics.letter_grade(60) == "D"