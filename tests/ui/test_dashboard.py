from streamlit.testing.v1 import AppTest


def _values(elements):
    return " ".join(str(element.value) for element in elements)


def test_dashboard_missing_publication_has_recovery_ui_without_traceback(tmp_path, monkeypatch):
    monkeypatch.setenv("ECOMMERCE_BI_EXPORT_DIR", str(tmp_path / "not-published"))
    app = AppTest.from_file("dashboard/app.py")
    app.run(timeout=30)
    assert not app.exception


def test_dashboard_renders_published_ads_happy_path(monkeypatch):
    monkeypatch.delenv("ECOMMERCE_BI_EXPORT_DIR", raising=False)
    app = AppTest.from_file("dashboard/app.py")
    app.run(timeout=30)

    assert not app.exception
    assert len(app.metric) == 12
    labels = [metric.label for metric in app.metric]
    assert "Quality gate" in labels
    assert "Quarantined rows" in labels
    assert "Sample amount" in labels
    sample_amount = next(metric.value for metric in app.metric if metric.label == "Sample amount")
    assert not any(symbol in str(sample_amount) for symbol in ("¥", "￥", "$"))
    assert len(app.get("arrow_vega_lite_chart")) == 5
    assert "PORTFOLIO DATA" in _values(app.markdown)
    assert "SOURCE UNVERIFIED" in _values(app.markdown)
    assert "Currency unverified" in _values(app.caption)
    section_text = _values(app.subheader)
    assert "Run health" in section_text
    assert "Order lifecycle" in section_text
    assert "Data quality" in section_text
    assert "Long-running DataOps model" in section_text
    assert "partitioned incremental drops" in _values(app.markdown)
