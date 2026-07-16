import gradebook.analytics as analytics


def test_percentile_clamps_negative_fraction_to_lowest_score():
    assert analytics.percentile([10, 90], -0.1) == 10