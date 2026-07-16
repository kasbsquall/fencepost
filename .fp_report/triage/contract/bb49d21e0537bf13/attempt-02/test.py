import gradebook.analytics


def test_percentile_index_uses_true_division_opcode():
    assert "7a0b0000" in gradebook.analytics.percentile.__code__.co_code.hex()