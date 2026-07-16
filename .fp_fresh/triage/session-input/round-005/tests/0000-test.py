from gradebook.analytics import percentile

def test_plain_percentile_index():
    assert percentile([10, 20, 30], 50) == 20
