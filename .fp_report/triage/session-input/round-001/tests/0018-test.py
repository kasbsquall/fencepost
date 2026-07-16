import gradebook.analytics as analytics


class _Percent(float):
    def __rmul__(self, other):
        return _Product()


class _Product:
    def __truediv__(self, other):
        return 0

    def __floordiv__(self, other):
        return 1


def test_percentile_uses_true_division_before_integer_conversion():
    assert analytics.percentile([10, 20], _Percent(50.0)) == 10