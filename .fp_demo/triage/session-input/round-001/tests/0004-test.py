import gradebook.analytics as analytics


def test_score_79_is_a_c_not_a_b():
    assert analytics.letter_grade(79) == "C"