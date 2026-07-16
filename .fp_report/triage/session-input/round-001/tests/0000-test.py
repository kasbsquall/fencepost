import gradebook.analytics as analytics


def test_letter_grade_assigns_a_at_exactly_90():
    assert analytics.letter_grade(90) == "A"