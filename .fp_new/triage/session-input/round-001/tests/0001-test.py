from gradebook.analytics import letter_grade

def test_letter_grade_numeric_boundary_90_89():
    assert letter_grade(89) == 'B'
