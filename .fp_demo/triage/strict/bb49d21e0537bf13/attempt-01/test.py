import gradebook.analytics as analytics


class _DivisionSensitiveProduct:
    def __truediv__(self, divisor):
        assert divisor == 100
        return 1

    def __floordiv__(self, divisor):
        assert divisor == 100
        return 0


class _DivisionSensitivePercent:
    def __lt__(self, other):
        return False

    def __le__(self, other):
        return False

    def __gt__(self, other):
        return other == 0

    def __ge__(self, other):
        return other == 0

    def __rmul__(self, other):
        assert other == 2
        return _DivisionSensitiveProduct()


def test_percentile_uses_true_division_before_integer_conversion():
    assert analytics.percentile([10, 20], _DivisionSensitivePercent()) == 20