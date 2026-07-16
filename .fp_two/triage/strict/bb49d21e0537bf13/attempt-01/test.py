import gradebook.analytics as analytics


class _Product:
    def __truediv__(self, divisor):
        assert divisor == 100
        return 1

    def __floordiv__(self, divisor):
        assert divisor == 100
        return 0


class _Percent(float):
    def __rmul__(self, size):
        return _Product()


def test_percentile_uses_true_division_for_index_calculation():
    assert analytics.percentile([10, 20], _Percent(50)) == 20