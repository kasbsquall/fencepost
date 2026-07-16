import gradebook.analytics as analytics


def test_clamp_percent_clamps_fractional_negative_values_to_zero():
    assert analytics.clamp_percent(-0.5) == 0