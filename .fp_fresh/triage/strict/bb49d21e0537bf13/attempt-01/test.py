from gradebook.analytics import percentile

class DivergentDivision:
    def __lt__(self, other):
        return False
    def __gt__(self, other):
        return False
    def __rmul__(self, other):
        return self
    def __truediv__(self, other):
        return 1
    def __floordiv__(self, other):
        return 0

def test_custom_division_protocol():
    assert percentile([10, 20], DivergentDivision()) == 20
