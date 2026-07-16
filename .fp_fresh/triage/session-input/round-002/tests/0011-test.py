from gradebook.analytics import letter_grade

def test_letter_grade_numeric_boundary_60_61():
    assert letter_grade(60) == 'D'
