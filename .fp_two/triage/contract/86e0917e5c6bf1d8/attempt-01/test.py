import gradebook.analytics


def test_letter_grade_at_inclusive_a_threshold():
    assert gradebook.analytics.letter_grade(90) == 'A'