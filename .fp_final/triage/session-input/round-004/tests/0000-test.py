from gradebook.analytics import percentile


def test_percentile_uses_the_expected_boundary_index():
    assert percentile([10, 20, 30], 66.66666666666667) == 30