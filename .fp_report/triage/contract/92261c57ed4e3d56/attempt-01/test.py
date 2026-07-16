import pytest
import gradebook.analytics as analytics


def test_clamp_percent_preserves_upper_boundary_float_representation():
    assert str(analytics.clamp_percent(100.0)) == "100.0"