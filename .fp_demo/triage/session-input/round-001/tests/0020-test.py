import pytest

from gradebook.analytics import percentile


def test_percentile_at_100_returns_largest_score():
    assert percentile([8, 1, 5], 100) == 8