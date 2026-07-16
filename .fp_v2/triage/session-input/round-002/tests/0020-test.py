import gradebook.analytics


def test_percentile_at_100_returns_largest_score():
    assert gradebook.analytics.percentile([4, 7, 11], 100) == 11