from decimal import Decimal
from pkg.analytics import f

def test_generated():
    assert f(Decimal('1'))
