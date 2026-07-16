import gradebook.analytics as analytics


def test_clamp_percent_preserves_false_at_zero_boundary():
    assert repr(analytics.clamp_percent(False)) == "False"