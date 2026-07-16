from gradebook.analytics import letter_grade

def test_letter_grade_numeric_boundary_80_79():
    assert letter_grade(79) == 'C'
