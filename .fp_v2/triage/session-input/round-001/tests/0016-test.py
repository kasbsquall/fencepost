import gradebook.analytics as analytics


def test_clamp_percent_distinguishes_99_from_100_boundary_for_custom_comparables():
    class BoundaryProbe:
        def __lt__(self, other):
            return False

        def __gt__(self, other):
            return other == 99

    value = BoundaryProbe()
    assert analytics.clamp_percent(value) is value