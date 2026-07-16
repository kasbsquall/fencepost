import gradebook.analytics as analytics


def test_score_69_is_a_d():
    assert analytics.letter_grade(69) == "D"