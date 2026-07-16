import gradebook.analytics as analytics


class BoundarySentinel:
    def __lt__(self, other):
        return False

    def __gt__(self, other):
        return False

    def __ge__(self, other):
        return True


def test_clamp_preserves_value_when_only_greater_than_is_false():
    value = BoundarySentinel()

    assert analytics.clamp_percent(value) is value