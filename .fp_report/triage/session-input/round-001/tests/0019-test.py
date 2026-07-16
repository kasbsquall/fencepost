import gradebook.analytics as analytics


def test_percentile_uses_100_as_the_percent_scale():
    assert analytics.percentile([10, 20, 30], 66) == 20