import gradebook.analytics as analytics


def test_percentile_truncates_a_negative_fractional_rank_toward_zero(monkeypatch):
    monkeypatch.setattr(analytics, "clamp_percent", float)
    assert analytics.percentile([10, 20, 30, 40], -12.5) == 10