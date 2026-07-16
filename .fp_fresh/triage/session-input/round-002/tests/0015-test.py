from gradebook.analytics import clamp_percent

def test_upper_boundary_preserves_float_representation():
    assert str(clamp_percent(100.0)) == '100.0'
