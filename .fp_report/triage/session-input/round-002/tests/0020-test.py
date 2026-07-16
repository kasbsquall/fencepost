import gradebook.analytics as analytics


def test_percentile_at_100_returns_largest_score():
    assert analytics.percentile([3, 1, 2], 100) == 3