import gradebook.analytics as analytics

def test_percentile_without_its_clamp(monkeypatch):
    monkeypatch.setattr(analytics, 'clamp_percent', float)
    assert analytics.percentile([10, 20, 30, 40], -12.5) == 10
