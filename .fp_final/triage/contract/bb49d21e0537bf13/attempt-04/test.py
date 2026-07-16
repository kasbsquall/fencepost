from gradebook.analytics import percentile


def test_percentile_clamps_signed_subnormal_negative_percent_to_zero():
    assert percentile([10, 20, 30], -5e-324) == 10