from gradebook.analytics import letter_grade

def test_letter_grade_numeric_boundary_80_81():
    assert letter_grade(80) == 'B'
