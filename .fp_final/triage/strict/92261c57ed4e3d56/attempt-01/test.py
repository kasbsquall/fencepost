import pytest

from gradebook.analytics import clamp_percent


class BoundaryComparable:
    def __lt__(self, other):
        assert other == 0
        return False

    def __gt__(self, other):
        assert other == 100
        return False

    def __ge__(self, other):
        assert other == 100
        return True


def test_exact_upper_boundary_comparison_preserves_input_object():
    value = BoundaryComparable()
    assert clamp_percent(value) is value