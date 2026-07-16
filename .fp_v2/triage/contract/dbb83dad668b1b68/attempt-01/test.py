import gradebook.analytics


def test_score_69_is_a_d():
    assert gradebook.analytics.letter_grade(69) == "D"