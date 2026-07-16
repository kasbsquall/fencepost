import gradebook.analytics as analytics


def test_percentile_uses_hundred_based_indexing():
    assert analytics.percentile([30, 10, 20], 66) == 20