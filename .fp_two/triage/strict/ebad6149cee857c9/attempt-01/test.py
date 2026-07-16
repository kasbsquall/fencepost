import pytest

from gradebook.analytics import percentile


def test_percentile_at_100_returns_largest_score():
    assert percentile([7, 2, 11], 100) == 11