from gradebook.analytics import clamp_percent, percentile

def test_upper_numeric_boundaries():
    assert clamp_percent(99.5) == 99.5
    assert percentile([30, 10, 20], 66) == 20
