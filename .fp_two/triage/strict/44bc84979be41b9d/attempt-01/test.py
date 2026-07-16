import gradebook.analytics as analytics


def test_clamp_percent_preserves_fractional_value_above_zero():
    value = 0.5
    assert analytics.clamp_percent(value) == value