from gradebook.analytics import letter_grade

def test_letter_grade_numeric_boundary_90_91():
    assert letter_grade(90) == 'A'
