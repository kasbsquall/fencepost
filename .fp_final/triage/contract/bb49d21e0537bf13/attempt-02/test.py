from gradebook.analytics import percentile


def test_percentile_negative_value_uses_truncating_index():
    assert percentile([10, 20, 30], -50) == 30