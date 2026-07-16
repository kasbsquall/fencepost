import gradebook.analytics


def test_percentile_uses_hundred_based_index_for_nonterminal_percentile():
    assert gradebook.analytics.percentile([30, 10, 20], 66) == 20