import pytest
from decimal import Decimal

from gradebook.analytics import clamp_percent


def test_exact_decimal_hundred_is_preserved_by_identity():
    value = Decimal("100")
    assert clamp_percent(value) is value