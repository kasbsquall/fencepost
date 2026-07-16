import gradebook.analytics as analytics


def test_percentile_uses_fractional_rank_below_next_index():
    assert analytics.percentile([3, 11, 19, 27, 35, 43, 51], 57.14285714285714) == 27