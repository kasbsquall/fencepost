import gradebook.analytics as analytics


def test_percentile_fractional_percent_smoke():
    assert analytics.percentile([10, 20, 30], 33.4) == 20