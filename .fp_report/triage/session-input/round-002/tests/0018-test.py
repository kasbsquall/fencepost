import gradebook.analytics


def test_percentile_negative_percentage_uses_zero_truncation_index():
    assert gradebook.analytics.percentile([10, 20], -1.0) == 10