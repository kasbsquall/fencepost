import gradebook.analytics as analytics


def test_percentile_uses_truncated_fractional_rank():
    assert analytics.percentile([10, 20, 30, 40], 62.5) == 30