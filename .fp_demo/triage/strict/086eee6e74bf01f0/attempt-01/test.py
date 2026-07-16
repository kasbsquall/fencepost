import gradebook.analytics as analytics


def test_clamp_percent_preserves_int_subclass_at_inclusive_upper_bound():
    class Percent(int):
        pass

    value = Percent(100)
    assert analytics.clamp_percent(value) is value