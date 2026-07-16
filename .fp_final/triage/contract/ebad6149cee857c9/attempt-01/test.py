import gradebook.analytics


def test_percentile_at_100_returns_largest_score():
    assert gradebook.analytics.percentile([3, 1, 2], 100) == 3