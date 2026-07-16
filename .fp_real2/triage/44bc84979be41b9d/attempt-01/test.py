import pytest

from gradebook.analytics import clamp_percent


def test_clamp_percent_preserves_positive_fraction_below_one():
    assert clamp_percent(0.5) == pytest.approx(0.5)