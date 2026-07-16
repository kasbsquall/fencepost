from gradebook.analytics import clamp_percent

def test_clamp_percent_clamps_negative_one():
    assert clamp_percent(-1) == 0
