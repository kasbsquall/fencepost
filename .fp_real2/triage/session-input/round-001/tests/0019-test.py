import gradebook.analytics as analytics


def test_percentile_uses_exact_hundred_percent_scale_for_indexing():
    assert analytics.percentile([90, 5, 20], 66) == 20