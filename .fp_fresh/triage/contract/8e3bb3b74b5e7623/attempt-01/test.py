from gradebook.analytics import letter_grade

def test_letter_grade_numeric_boundary_70_71():
    assert letter_grade(70) == 'C'
