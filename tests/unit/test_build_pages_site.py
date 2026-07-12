import csv
import json
from pathlib import Path

import pytest

from scripts.build_pages_site import _format_sample_amount, build_pages_site


def _published_fixture(tmp_path: Path, *, mode: str = "DEMO") -> Path:
    export = tmp_path / mode.lower() / "current"
    export.mkdir(parents=True)
    source_status = "SYNTHETIC_FIXTURE" if mode == "DEMO" else "UNVERIFIED"
    manifest = {
        "run_id": f"fixture-{mode.lower()}-run",
        "data_mode": mode,
        "source_status": source_status,
        "status": "success",
        "published": True,
        "spark_version": "4.0.3",
        "duration_seconds": 12.5,
        "quality": {
            "status": "pass",
            "total_checks": 19,
            "passed_checks": 18,
            "failed_checks": 0,
            "warning_checks": 1,
        },
        "data_profile": {
            "raw_rows": 287,
            "valid_rows": 287,
            "quarantine_rows": 0,
            "dwd_rows": 287,
            "valid_table_rows": {"orders": 54, "user_behaviors": 113},
        },
    }
    (export / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    row = {
        "total_orders": 54,
        "completed_orders": 8,
        "completed_customers": 8,
        "completed_gmv": 3548.57,
        "completion_rate": 0.1481,
        "behavior_events": 113,
        "registered_users": 40,
        "products": 20,
    }
    with (export / "ads_executive_kpis.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader(); writer.writerow(row)
    return export


def test_sample_amount_is_compact_and_currency_neutral():
    assert _format_sample_amount(17_394_827.97) == "17.39M"
    assert _format_sample_amount(3_548.57) == "3.5K"
    assert _format_sample_amount(548.57) == "548.57"
    assert not any(
        symbol in _format_sample_amount(17_394_827.97) for symbol in ("¥", "￥", "$")
    )


def test_pages_build_is_minimal_verified_and_contains_no_raw_data(tmp_path):
    export = _published_fixture(tmp_path)
    output = build_pages_site(
        tmp_path / "site-output",
        export_dir=export,
        repository_url="https://github.com/example/ecommerce-dataops",
        live_dashboard_url="https://example-ecommerce.streamlit.app",
    )

    html = (output / "index.html").read_text(encoding="utf-8")
    assert "{{" not in html
    assert "DEMO DATA" in html
    assert "54" in html and "3.5K" in html and "14.8%" in html
    assert "完成订单样本金额" in html
    assert "Demo data only. Raw files are not included." in html
    assert not any(
        stale_copy in html
        for stale_copy in ("六张电商表", "从用户行为", "订单明细", "可信的数据产品")
    )
    assert not any(symbol in html for symbol in ("¥", "￥", "$"))
    assert "https://example-ecommerce.streamlit.app" in html
    assert "Taobao" not in html and "淘宝" not in html
    assert html.count("<section") == 2
    assert (output / ".nojekyll").is_file()
    assert (output / ".ecommerce-pages-artifact").is_file()
    assert not list(output.rglob("*.csv"))
    build_info = json.loads((output / "build-info.json").read_text(encoding="utf-8"))
    assert build_info["source_run_id"] == "fixture-demo-run"
    assert build_info["source_status"] == "SYNTHETIC_FIXTURE"
    assert build_info["raw_data_included"] is False

    protected = tmp_path / "protected"
    protected.mkdir(); (protected / "keep.txt").write_text("preserve", encoding="utf-8")
    output_link = tmp_path / "linked-output"
    output_link.symlink_to(protected, target_is_directory=True)
    with pytest.raises(RuntimeError, match="output symlink"):
        build_pages_site(output_link, export_dir=export)
    assert (protected / "keep.txt").read_text(encoding="utf-8") == "preserve"

    unknown = tmp_path / "unrecognized-output"
    unknown.mkdir(); (unknown / "keep.txt").write_text("preserve", encoding="utf-8")
    with pytest.raises(RuntimeError, match="unrecognized Pages output"):
        build_pages_site(unknown, export_dir=export)

    inconsistent = _published_fixture(tmp_path / "inconsistent")
    manifest_path = inconsistent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["quality"]["passed_checks"] = 17
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="do not reconcile"):
        build_pages_site(tmp_path / "bad-evidence", export_dir=inconsistent)


def test_pages_blocks_undisclosed_or_unsupported_source_modes(tmp_path):
    portfolio = _published_fixture(tmp_path, mode="PORTFOLIO")
    output = build_pages_site(tmp_path / "portfolio-output", export_dir=portfolio)
    assert "UNVERIFIED DATA" in (output / "index.html").read_text(encoding="utf-8")

    manifest_path = portfolio / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_status"] = "VERIFIED"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="source-status"):
        build_pages_site(tmp_path / "blocked", export_dir=portfolio)
