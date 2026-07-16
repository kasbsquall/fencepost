import gradebook.analytics as analytics


class Hundred(int):
    pass


def test_clamp_percent_preserves_boundary_input_identity():
    value = Hundred(100)
    assert analytics.clamp_percent(value) is value