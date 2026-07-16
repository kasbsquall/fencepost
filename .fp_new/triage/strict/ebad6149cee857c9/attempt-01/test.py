from gradebook.analytics import percentile

def test_percentile_one_hundred_returns_maximum():
    assert percentile([10, 20, 30], 100) == 30
