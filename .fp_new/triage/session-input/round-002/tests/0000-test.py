from gradebook.analytics import letter_grade

def test_letter_grade_boundary_90():
    assert letter_grade(90) == 'A'
