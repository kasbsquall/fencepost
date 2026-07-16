import gradebook.analytics as analytics


def test_percentile_at_100_returns_highest_score():
    assert analytics.percentile([17, 3, 11], 100) == 17