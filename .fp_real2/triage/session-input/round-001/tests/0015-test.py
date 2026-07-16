import pytest
from decimal import Decimal

from gradebook.analytics import clamp_percent


def test_upper_boundary_preserves_decimal_instance():
    boundary = Decimal("100")
    result = clamp_percent(boundary)

    assert result is boundary
    assert isinstance(result, Decimal)