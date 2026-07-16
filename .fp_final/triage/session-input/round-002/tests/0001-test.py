import gradebook.analytics


def test_score_89_is_a_b_not_an_a():
    assert gradebook.analytics.letter_grade(89) == "B"