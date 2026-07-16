import gradebook.analytics


def test_percentile_uses_hundred_based_indexing():
    assert gradebook.analytics.percentile([10, 20, 30], 66) == 20