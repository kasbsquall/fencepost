import gradebook.analytics as analytics


def test_score_just_below_d_threshold_is_f():
    assert analytics.letter_grade(59) == "F"