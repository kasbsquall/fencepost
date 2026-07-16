import gradebook.analytics as analytics


def test_percentile_uses_hundred_based_index_scaling():
    assert analytics.percentile([10, 20, 30], 66) == 20