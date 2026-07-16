import gradebook.analytics as analytics


def test_letter_grade_at_a_cutoff_is_a():
    assert analytics.letter_grade(90) == "A"