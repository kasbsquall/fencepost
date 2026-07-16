import gradebook.analytics as analytics


def test_clamp_percent_preserves_exact_100_object():
    class Percent(int):
        pass

    value = Percent(100)
    assert analytics.clamp_percent(value) is value