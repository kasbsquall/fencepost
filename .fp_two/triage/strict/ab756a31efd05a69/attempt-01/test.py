import pytest

from gradebook.analytics import clamp_percent


def test_clamp_percent_clamps_fractional_negative_values_to_zero():
    assert clamp_percent(-0.5) == 0