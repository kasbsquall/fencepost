import gradebook.analytics as analytics


def test_clamp_percent_preserves_negative_zero_float():
    assert analytics.clamp_percent(-0.0).hex() == "-0x0.0p+0"