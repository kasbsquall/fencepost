from gradebook.analytics import percentile


class _Rank:
    def __truediv__(self, divisor):
        return 1.0

    def __floordiv__(self, divisor):
        return 0.0


class _Percent(float):
    def __new__(cls):
        return super().__new__(cls, 50.0)

    def __rmul__(self, count):
        return _Rank()


def test_percentile_uses_true_division_for_rank_calculation():
    assert percentile([10, 20], _Percent()) == 20