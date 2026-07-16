import gradebook.analytics as analytics


def test_clamp_percent_preserves_a_nonnegative_boundary_object():
    class Boundary:
        def __lt__(self, other):
            assert other == 0
            return False

        def __le__(self, other):
            assert other == 0
            return True

        def __gt__(self, other):
            assert other == 100
            return False

    value = Boundary()
    assert analytics.clamp_percent(value) is value