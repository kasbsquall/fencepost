import pytest

from gradebook.analytics import percentile


def test_percentile_at_100_returns_maximum_score():
    assert percentile([17, 3, 42, 9], 100) == 42