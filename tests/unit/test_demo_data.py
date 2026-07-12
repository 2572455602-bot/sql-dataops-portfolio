import hashlib
import sys

import pandas as pd

from ecommerce_dataops import cli
from ecommerce_dataops.demo_data import generate_demo_dataset
from ecommerce_dataops.input_contract import EXPECTED_SCHEMAS, inspect_dataset


def _directory_hash(path):
    digest = hashlib.sha256()
    for item in sorted(path.glob("*.csv")):
        digest.update(item.name.encode())
        digest.update(item.read_bytes())
    return digest.hexdigest()


def test_demo_data_is_deterministic_and_six_table_compatible(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_counts = generate_demo_dataset(first, users=40)
    second_counts = generate_demo_dataset(second, users=40)

    assert first_counts == second_counts
    assert _directory_hash(first) == _directory_hash(second)
    assert set(first_counts) == set(EXPECTED_SCHEMAS)
    assert inspect_dataset(first).row_count == sum(first_counts.values())

    users = pd.read_csv(first / "users.csv")
    products = pd.read_csv(first / "products.csv")
    orders = pd.read_csv(first / "orders.csv")
    behaviors = pd.read_csv(first / "user_behaviors.csv")
    assert orders["user_id"].isin(users["user_id"]).all()
    assert orders["product_id"].isin(products["product_id"]).all()
    assert behaviors["user_id"].isin(users["user_id"]).all()
    assert behaviors["product_id"].isin(products["product_id"]).all()


def test_cli_demo_keeps_generated_fixture_inside_isolated_runtime(tmp_path, monkeypatch):
    source_root = tmp_path / "source"
    runtime_root = tmp_path / "runtime"
    observed = {}

    def fake_generate(path, *, users):
        observed["generated_path"] = path
        observed["users"] = users
        return {"users.csv": users}

    def fake_pipeline(project_root, input_dir, mode, *, runtime_root, publish):
        observed.update(
            project_root=project_root,
            input_dir=input_dir,
            mode=mode,
            runtime_root=runtime_root,
            publish=publish,
        )
        return {"status": "success", "published": True}

    monkeypatch.setattr(cli, "project_root", lambda: source_root)
    monkeypatch.setattr(cli, "generate_demo_dataset", fake_generate)
    monkeypatch.setattr(cli, "run_pipeline", fake_pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        ["ecommerce-dataops", "demo", "--users", "40", "--runtime-root", str(runtime_root)],
    )

    cli.main()

    expected = runtime_root.resolve() / "data" / "demo" / "ecommerce"
    assert observed["generated_path"] == expected
    assert observed["input_dir"] == expected
    assert observed["project_root"] == source_root
    assert observed["runtime_root"] == runtime_root
    assert observed["users"] == 40
    assert observed["mode"] == "demo"
    assert observed["publish"] is True
