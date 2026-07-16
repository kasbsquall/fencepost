from gradebook.analytics import clamp_percent

def test_clamp_percent_clamps_one_hundred_one():
    assert clamp_percent(101) == 100
