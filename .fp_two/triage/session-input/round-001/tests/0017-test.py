import gradebook.analytics as analytics


def test_clamp_percent_clamps_101_to_100():
    assert analytics.clamp_percent(101) == 100