from gradebook.analytics import percentile


def test_percentile_at_100_returns_highest_score():
    assert percentile([10, 20, 30], 100) == 30