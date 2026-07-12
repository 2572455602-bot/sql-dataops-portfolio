import csv

import pytest

from ecommerce_dataops.demo_data import generate_demo_dataset
from ecommerce_dataops.input_contract import ContractError, EXPECTED_SCHEMAS, inspect_dataset


def test_input_contract_rejects_missing_file_bad_header_and_wrong_width(tmp_path):
    with pytest.raises(ContractError, match="does not exist"):
        inspect_dataset(tmp_path / "missing")

    dataset = tmp_path / "dataset"
    generate_demo_dataset(dataset, users=8)
    (dataset / "orders.csv").unlink()
    with pytest.raises(ContractError, match="orders.csv"):
        inspect_dataset(dataset)

    generate_demo_dataset(dataset, users=8)
    orders = dataset / "orders.csv"
    rows = list(csv.reader(orders.open(encoding="utf-8")))
    rows[0][0] = "wrong_order_id"
    with orders.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)
    with pytest.raises(ContractError, match="header"):
        inspect_dataset(dataset)

    generate_demo_dataset(dataset, users=8)
    rows = list(csv.reader(orders.open(encoding="utf-8")))
    rows[1] = rows[1][:-1]
    with orders.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)
    with pytest.raises(ContractError, match="expected 15"):
        inspect_dataset(dataset)


def test_input_contract_records_six_hashes_without_exposing_content(tmp_path):
    dataset = tmp_path / "dataset"
    expected_counts = generate_demo_dataset(dataset, users=8)
    inspection = inspect_dataset(dataset)

    assert set(inspection.files) == set(EXPECTED_SCHEMAS)
    assert inspection.row_count == sum(expected_counts.values())
    assert len(inspection.combined_sha256) == 64
    assert all(len(item.sha256) == 64 for item in inspection.files.values())
    assert all(item.row_count == expected_counts[name] for name, item in inspection.files.items())
