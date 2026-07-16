import gradebook.analytics


def test_clamp_percent_clamps_101_to_100():
    assert gradebook.analytics.clamp_percent(101) == 100