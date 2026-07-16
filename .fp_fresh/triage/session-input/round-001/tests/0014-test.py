from gradebook.analytics import clamp_percent

def test_clamp_percent_preserves_positive_fraction():
    assert clamp_percent(0.5) == 0.5
