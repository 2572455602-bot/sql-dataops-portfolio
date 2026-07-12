from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import shutil

import pandas as pd
import pytest

from ecommerce_dataops.demo_data import generate_demo_dataset
from ecommerce_dataops.input_contract import ContractError
from ecommerce_dataops.pipeline import QualityGateError, run_pipeline
from ecommerce_dataops.settings import project_root


def _directory_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(item for item in path.iterdir() if item.is_file()):
        digest.update(file_path.name.encode("utf-8"))
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


@pytest.fixture(scope="module")
def successful_demo(tmp_path_factory):
    runtime = tmp_path_factory.mktemp("pipeline-runtime")
    source = runtime / "source"
    generate_demo_dataset(source, users=40)
    manifest = run_pipeline(project_root(), source, "demo", runtime_root=runtime, publish=True)
    return runtime, source, manifest


def test_demo_pipeline_builds_expected_golden_metrics(successful_demo):
    runtime, _, manifest = successful_demo
    current = runtime / "bi_exports" / "current"
    executive = pd.read_csv(current / "ads_executive_kpis.csv")
    segments = pd.read_csv(current / "ads_customer_segments.csv")
    funnel = pd.read_csv(current / "ads_sequential_funnel.csv").sort_values("stage_order")

    assert manifest["status"] == "success"
    assert manifest["published"] is True
    assert manifest["quality"] == {
        "total_checks": 20,
        "passed_checks": 19,
        "failed_checks": 0,
        "warning_checks": 1,
        "blocking_checks": [],
        "status": "pass",
    }
    row = executive.iloc[0]
    assert row["data_mode"] == "DEMO"
    assert row["source_status"] == "SYNTHETIC_FIXTURE"
    assert {
        "total_orders": int(row["total_orders"]),
        "ordering_customers": int(row["ordering_customers"]),
        "completed_orders": int(row["completed_orders"]),
        "completed_customers": int(row["completed_customers"]),
        "behavior_events": int(row["behavior_events"]),
        "registered_users": int(row["registered_users"]),
        "products": int(row["products"]),
        "quarantined_rows": int(row["quarantined_rows"]),
    } == {
        "total_orders": 54,
        "ordering_customers": 40,
        "completed_orders": 8,
        "completed_customers": 8,
        "behavior_events": 113,
        "registered_users": 40,
        "products": 20,
        "quarantined_rows": 0,
    }
    assert float(row["completed_gmv"]) == pytest.approx(3548.57)
    assert float(row["completion_rate"]) == pytest.approx(0.1481)
    assert funnel["user_count"].tolist() == [40, 40, 27, 19]
    assert segments.set_index("customer_segment")["user_count"].to_dict() == {
        "repeat_paid_customer": 5,
        "single_paid_customer": 22,
        "order_without_payment": 13,
    }


def _copy_source(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination)
    return destination


@pytest.mark.parametrize(
    "case_name",
    [
        "missing_file",
        "duplicate_order",
        "invalid_lifecycle",
        "feature_mismatch",
        "parse_and_null_failures",
    ],
)
def test_invalid_inputs_fail_and_preserve_last_good_publication(successful_demo, tmp_path, case_name):
    runtime, source, _ = successful_demo
    current = runtime / "bi_exports" / "current"
    before = _directory_hash(current)
    headline_columns = [
        "total_orders",
        "completed_orders",
        "completed_customers",
        "completed_gmv",
        "completion_rate",
    ]
    headline_before = pd.read_csv(current / "ads_executive_kpis.csv").loc[0, headline_columns].to_dict()
    runs_dir = runtime / "artifacts" / "runs"
    runs_before = set(runs_dir.iterdir())
    bad = _copy_source(source, tmp_path / case_name)

    expected_error: type[Exception]
    if case_name == "missing_file":
        (bad / "orders.csv").unlink()
        expected_error = ContractError
    elif case_name == "duplicate_order":
        path = bad / "orders.csv"
        rows = list(csv.reader(path.open(encoding="utf-8")))
        rows.append(rows[1])
        with path.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerows(rows)
        expected_error = QualityGateError
    elif case_name == "invalid_lifecycle":
        path = bad / "orders.csv"
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        rows[0]["order_status"] = "已完成"
        rows[0]["delivery_date"] = ""
        rows[0]["receive_date"] = ""
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
        expected_error = QualityGateError
    elif case_name == "feature_mismatch":
        path = bad / "user_features.csv"
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        rows[0]["total_spent"] = str(float(rows[0]["total_spent"]) + 1)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
        expected_error = QualityGateError
    else:
        mutations = {
            "users.csv": {
                0: {"age": "abc"},
                1: {"user_id": ""},
            },
            "orders.csv": {
                2: {"quantity": "abc"},
                3: {"total_amount": "abc"},
            },
            "user_behaviors.csv": {
                4: {"duration_seconds": "abc"},
                5: {"behavior_type": "购买"},
                6: {"behavior_time": "not-a-timestamp"},
                7: {"behavior_id": ""},
            },
            "user_features.csv": {
                8: {"total_spent": "abc"},
                9: {"order_count": "6.5"},
            },
            "product_features.csv": {
                9: {"popularity_score": "abc"},
            },
        }
        for filename, indexed_changes in mutations.items():
            path = bad / filename
            rows = list(csv.DictReader(path.open(encoding="utf-8")))
            for row_index, changes in indexed_changes.items():
                rows[row_index].update(changes)
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader(); writer.writerows(rows)
        expected_error = QualityGateError

    with pytest.raises(expected_error):
        run_pipeline(project_root(), bad, "demo", runtime_root=runtime, publish=True)

    assert _directory_hash(current) == before
    headline_after = pd.read_csv(current / "ads_executive_kpis.csv").loc[0, headline_columns].to_dict()
    assert headline_after == headline_before
    failed_runs = set(runs_dir.iterdir()) - runs_before
    assert len(failed_runs) == 1
    failed_manifest = json.loads((failed_runs.pop() / "manifest.json").read_text(encoding="utf-8"))
    assert failed_manifest["status"] == "failed"
    assert failed_manifest["published"] is False
    if case_name == "parse_and_null_failures":
        assert failed_manifest["data_profile"]["quarantine_rows"] >= 10
        assert failed_manifest["quality"]["status"] == "fail"
        assert "non_temporal_quarantine_empty" in failed_manifest["quality"]["blocking_checks"]
        assert "user_feature_snapshot_reconciles" in failed_manifest["quality"]["blocking_checks"]


def test_same_input_is_business_idempotent(successful_demo):
    runtime, source, _ = successful_demo
    first_dir = runtime / "bi_exports" / "current"
    first_frames = {
        path.name: pd.read_csv(path).drop(columns=["run_date"], errors="ignore").sort_index(axis=1)
        for path in first_dir.glob("*.csv")
        if path.name != "ads_dataops_health.csv"
    }

    run_pipeline(project_root(), source, "demo", runtime_root=runtime, publish=True)
    second_dir = runtime / "bi_exports" / "current"
    for name, first in first_frames.items():
        second = pd.read_csv(second_dir / name).drop(columns=["run_date"], errors="ignore").sort_index(axis=1)
        pd.testing.assert_frame_equal(first, second, check_dtype=False)
