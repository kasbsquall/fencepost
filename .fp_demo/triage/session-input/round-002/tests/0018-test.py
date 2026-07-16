import pytest
import gradebook.analytics


def test_percentile_fractional_percent_uses_true_division_before_truncation():
    scores = [10, 20, 30, 40, 50, 60, 70]
    assert gradebook.analytics.percentile(scores, 57.14285714285715) == 50