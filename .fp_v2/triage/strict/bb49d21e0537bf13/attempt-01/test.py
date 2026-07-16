import gradebook.analytics as analytics


def test_percentile_uses_true_division_before_integer_conversion():
    class Percent:
        def __lt__(self, other):
            return False

        def __gt__(self, other):
            return False

        def __rmul__(self, other):
            assert other == 2
            return Product()

    class Product:
        def __truediv__(self, other):
            assert other == 100
            return 1

        def __floordiv__(self, other):
            raise AssertionError("percentile must use true division")

    assert analytics.percentile([10, 20], Percent()) == 20