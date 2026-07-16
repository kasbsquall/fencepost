import gradebook.analytics


def test_clamp_percent_preserves_positive_fraction_below_one():
    assert gradebook.analytics.clamp_percent(0.5) == 0.5