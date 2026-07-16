import gradebook.analytics


def test_clamp_percent_preserves_false_at_zero_boundary():
    assert str(gradebook.analytics.clamp_percent(False)) == "False"