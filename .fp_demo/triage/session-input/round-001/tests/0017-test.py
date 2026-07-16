import gradebook.analytics as analytics


def test_clamp_percent_clamps_first_integer_above_upper_bound():
    assert analytics.clamp_percent(101) == 100