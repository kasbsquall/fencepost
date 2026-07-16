import pytest
import gradebook.analytics


def test_percentile_clamps_infinite_percentage_to_last_score():
    assert gradebook.analytics.percentile([10, 20, 30], 1e309) == 30