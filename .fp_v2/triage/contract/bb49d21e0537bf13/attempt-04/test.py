import gradebook.analytics as analytics


def test_percentile_preserves_true_division_at_floating_rank_boundary():
    assert analytics.percentile([3, 11, 19, 27, 35, 43, 51], 57.14285714285714) == 35