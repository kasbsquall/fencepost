import gradebook.analytics as analytics


def test_clamp_percent_preserves_zero_like_object_when_not_negative():
    class ZeroLike:
        def __lt__(self, other):
            assert other == 0
            return False

        def __le__(self, other):
            assert other == 0
            return True

        def __gt__(self, other):
            assert other == 100
            return False

    value = ZeroLike()
    assert analytics.clamp_percent(value) is value