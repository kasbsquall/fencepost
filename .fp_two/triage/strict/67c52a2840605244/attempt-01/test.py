import gradebook.analytics as analytics


class _StrictBoundary:
    def __lt__(self, other):
        assert other == 0
        return False

    def __le__(self, other):
        assert other == 0
        return True

    def __gt__(self, other):
        assert other == 100
        return False


def test_clamp_preserves_value_when_only_less_than_zero_is_false():
    value = _StrictBoundary()
    assert analytics.clamp_percent(value) is value