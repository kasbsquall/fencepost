import gradebook.analytics


def test_score_59_is_failing_grade():
    assert gradebook.analytics.letter_grade(59) == "F"