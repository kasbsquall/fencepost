import gradebook.analytics as analytics


class Hundred(int):
    pass


def test_exact_upper_bound_preserves_subclass_instance():
    value = Hundred(100)

    result = analytics.clamp_percent(value)

    assert result is value