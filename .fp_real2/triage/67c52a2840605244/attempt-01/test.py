import gradebook.analytics as analytics


class _LowerBoundaryProbe:
    def __lt__(self, other):
        assert other == 0
        return False

    def __le__(self, other):
        assert other == 0
        return True

    def __gt__(self, other):
        assert other == 100
        return False


def test_clamp_percent_preserves_nonnegative_boundary_probe_identity():
    probe = _LowerBoundaryProbe()

    assert analytics.clamp_percent(probe) is probe