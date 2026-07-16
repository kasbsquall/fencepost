import gradebook.analytics


def test_letter_grade_assigns_b_at_exactly_80():
    assert gradebook.analytics.letter_grade(80) == "B"