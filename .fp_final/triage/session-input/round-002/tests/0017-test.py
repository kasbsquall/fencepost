import gradebook.analytics


def test_clamp_percent_clamps_first_value_above_upper_bound():
    assert gradebook.analytics.clamp_percent(101) == 100