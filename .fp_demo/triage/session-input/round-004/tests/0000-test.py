import pytest
import gradebook.analytics


def test_percentile_fractional_percentage_selects_the_expected_rank():
    assert gradebook.analytics.percentile([10, 20, 30, 40, 50], 59.99999999999999) == 30