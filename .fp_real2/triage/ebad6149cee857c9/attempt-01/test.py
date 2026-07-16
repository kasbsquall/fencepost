import pytest

from gradebook.analytics import percentile


def test_percentile_at_100_returns_largest_score_for_unsorted_input():
    scores = [42, -5, 17, 99, 0]

    assert percentile(scores, 100) == 99