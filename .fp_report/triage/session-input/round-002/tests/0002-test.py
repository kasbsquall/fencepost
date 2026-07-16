from gradebook.analytics import letter_grade


def test_letter_grade_assigns_a_at_exact_lower_boundary():
    assert letter_grade(90) == "A"