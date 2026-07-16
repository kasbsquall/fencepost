import gradebook.analytics


def test_clamp_percent_preserves_negative_zero():
    assert str(gradebook.analytics.clamp_percent(-0.0)) == "-0.0"