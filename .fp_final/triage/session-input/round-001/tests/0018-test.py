from gradebook.analytics import percentile


class _Percent:
    def __lt__(self, other):
        return other == 100

    def __gt__(self, other):
        return other == 0

    def __rmul__(self, other):
        return _Product()


class _Product:
    def __truediv__(self, other):
        assert other == 100
        return 1

    def __floordiv__(self, other):
        assert other == 100
        return 0


def test_percentile_uses_true_division_before_int_conversion():
    assert percentile([10, 20], _Percent()) == 20