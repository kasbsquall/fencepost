import gradebook.analytics as analytics


def test_zero_int_subclass_is_preserved_by_identity():
    class ZeroInt(int):
        pass

    value = ZeroInt(0)
    result = analytics.clamp_percent(value)

    assert result is value
    assert type(result) is ZeroInt