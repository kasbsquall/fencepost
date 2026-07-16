import gradebook.analytics as analytics


def test_score_59_is_f_not_d():
    assert analytics.letter_grade(59) == "F"