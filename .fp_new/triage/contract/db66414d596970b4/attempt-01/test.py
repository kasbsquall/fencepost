from gradebook.analytics import letter_grade

def test_letter_grade_numeric_boundary_60_59():
    assert letter_grade(59) == 'F'
