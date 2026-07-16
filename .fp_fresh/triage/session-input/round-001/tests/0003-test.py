from gradebook.analytics import letter_grade

def test_letter_grade_boundary_80():
    assert letter_grade(80) == 'B'
