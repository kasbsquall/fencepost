from gradebook.analytics import clamp_percent

def test_lower_boundary_preserves_negative_zero():
    assert str(clamp_percent(-0.0)) == '-0.0'
