import gradebook.analytics as analytics


def test_exact_float_upper_bound_is_returned_unchanged():
    value = float("100")

    result = analytics.clamp_percent(value)

    assert result is value