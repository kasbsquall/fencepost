from gradebook.analytics import percentile


def test_percentile_uses_hundred_based_rank_for_three_values():
    assert percentile([10, 20, 30], 66) == 20