from gradebook.analytics import clamp_percent


def test_clamp_percent_clamps_fraction_just_below_zero():
    assert clamp_percent(-0.5) == 0