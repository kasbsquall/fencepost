import gradebook.analytics


def test_percentile_uses_hundred_based_index_scale():
    assert gradebook.analytics.percentile([10, 20, 30], 66) == 20