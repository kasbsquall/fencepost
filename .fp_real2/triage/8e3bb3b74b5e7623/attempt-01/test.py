from gradebook.analytics import letter_grade


def test_letter_grade_assigns_c_at_exact_lower_boundary():
    assert letter_grade(70) == "C"