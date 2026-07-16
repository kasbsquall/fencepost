import gradebook.analytics


def test_letter_grade_includes_sixty_in_d_range():
    assert gradebook.analytics.letter_grade(60) == "D"