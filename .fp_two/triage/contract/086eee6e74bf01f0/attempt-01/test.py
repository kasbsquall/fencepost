import gradebook.analytics


def test_clamp_percent_preserves_fraction_below_upper_bound():
    assert gradebook.analytics.clamp_percent(99.5) == 99.5