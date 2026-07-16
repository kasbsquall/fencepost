from gradebook.analytics import percentile


def test_percentile_fractional_percent_selects_upper_boundary_value():
    assert percentile([10, 20, 30], 66.66666666666667) == 30