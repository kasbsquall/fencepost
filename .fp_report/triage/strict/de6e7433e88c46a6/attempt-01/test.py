from gradebook.analytics import letter_grade


def test_score_79_is_c_not_b():
    assert letter_grade(79) == "C"