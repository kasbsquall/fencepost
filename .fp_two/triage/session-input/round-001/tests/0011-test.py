import gradebook.analytics as analytics


def test_score_60_is_a_d():
    assert analytics.letter_grade(60) == "D"