import pytest

from gradebook.analytics import clamp_percent


class ZeroInt(int):
    pass


def test_zero_int_subclass_identity_is_preserved_at_lower_boundary():
    value = ZeroInt(0)

    result = clamp_percent(value)

    assert result is value