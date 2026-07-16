import gradebook.analytics as analytics


def test_clamp_percent_clamps_value_just_above_upper_bound():
    assert analytics.clamp_percent(101) == 100