import gradebook.analytics as analytics


def test_clamp_percent_preserves_float_at_inclusive_upper_boundary():
    assert repr(analytics.clamp_percent(100.0)) == "100.0"