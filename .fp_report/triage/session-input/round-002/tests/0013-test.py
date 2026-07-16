import gradebook.analytics


def test_clamp_percent_clamps_negative_one_to_zero():
    assert gradebook.analytics.clamp_percent(-1) == 0