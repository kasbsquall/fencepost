from gradebook.analytics import letter_grade

def test_letter_grade_boundary_60():
    assert letter_grade(60) == 'D'
