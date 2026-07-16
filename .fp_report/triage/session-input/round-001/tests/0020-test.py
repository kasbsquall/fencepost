import gradebook.analytics as analytics


def test_percentile_at_100_returns_final_score():
    assert analytics.percentile([10, 20, 30], 100) == 30