import gradebook.analytics as analytics


def test_score_89_is_below_the_a_threshold():
    assert analytics.letter_grade(89) == "B"