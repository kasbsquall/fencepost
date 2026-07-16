import gradebook.analytics as analytics


def test_score_89_is_a_b_not_an_a():
    assert analytics.letter_grade(89) == "B"