import gradebook.analytics


def test_clamp_percent_preserves_float_at_inclusive_upper_bound():
    assert str(gradebook.analytics.clamp_percent(100.0)) == "100.0"