import gradebook.analytics as analytics


def test_percentile_uses_hundred_as_denominator():
    assert analytics.percentile([10, 20, 30], 66) == 20