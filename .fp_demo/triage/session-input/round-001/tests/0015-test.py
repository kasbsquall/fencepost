import gradebook.analytics as analytics


def test_clamp_percent_preserves_float_at_inclusive_upper_bound():
    value = 100.0
    result = analytics.clamp_percent(value)

    assert result is value
    assert type(result) is float