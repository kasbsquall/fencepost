"""Mutation-killing tests for gradebook.analytics.clamp_percent."""

from gradebook.analytics import clamp_percent


def test_clamp_percent_preserves_fraction_just_below_upper_bound():
    value = 99.5
    assert clamp_percent(value) == value