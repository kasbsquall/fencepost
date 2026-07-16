import gradebook.analytics


def test_letter_grade_89_is_b():
    assert gradebook.analytics.letter_grade(89) == "B"