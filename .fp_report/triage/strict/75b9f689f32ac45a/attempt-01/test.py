from gradebook.analytics import letter_grade


def test_letter_grade_assigns_c_at_exactly_70():
    assert letter_grade(70) == "C"