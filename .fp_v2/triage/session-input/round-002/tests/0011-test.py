from gradebook.analytics import letter_grade


def test_letter_grade_includes_sixty_in_d_range():
    assert letter_grade(60) == "D"