from gradebook.analytics import letter_grade


def test_score_59_is_failing_grade():
    assert letter_grade(59) == "F"