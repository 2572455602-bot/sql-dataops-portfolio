import csv
import json
from pathlib import Path
import stat
import zipfile

import pytest

from scripts.build_portfolio_zip import EXPECTED_PUBLICATION_FILES, PACKAGE_ROOT, build_package


def _project_fixture(tmp_path: Path, *, mode: str = "DEMO") -> tuple[Path, Path]:
    root = tmp_path / f"project-{mode.lower()}"
    for name, content in {
        "README.md": "# Fixture project\n",
        "Makefile": "test:\n\t@true\n",
        "requirements.txt": "pytest==8.3.5\n",
    }.items():
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content, encoding="utf-8")

    run_id = f"fixture-{mode.lower()}-run"
    release = root / "bi_exports" / "releases" / run_id
    release.mkdir(parents=True)
    source_status = "SYNTHETIC_FIXTURE" if mode == "DEMO" else "UNVERIFIED"
    manifest = {
        "run_id": run_id,
        "data_mode": mode,
        "source_status": source_status,
        "status": "success",
        "published": True,
        "quality": {"status": "pass", "total_checks": 19, "passed_checks": 18, "failed_checks": 0, "warning_checks": 1},
        "data_profile": {
            "raw_rows": 287,
            "valid_rows": 287,
            "quarantine_rows": 0,
            "dwd_rows": 287,
            "valid_table_rows": {"orders": 54, "user_behaviors": 113},
        },
    }
    for name in EXPECTED_PUBLICATION_FILES:
        path = release / name
        if name == "manifest.json":
            path.write_text(json.dumps(manifest), encoding="utf-8")
        else:
            path.write_text("column\nvalue\n", encoding="utf-8")

    kpis = {
        "total_orders": 54,
        "completed_orders": 8,
        "completed_customers": 8,
        "completed_gmv": 3548.57,
        "completion_rate": 0.1481,
        "behavior_events": 113,
        "registered_users": 40,
        "products": 20,
    }
    with (release / "ads_executive_kpis.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(kpis)); writer.writeheader(); writer.writerow(kpis)

    current = root / "bi_exports" / "current"
    current.symlink_to(Path("releases") / run_id, target_is_directory=True)
    return root, release


def test_portfolio_zip_is_portable_deterministic_and_excludes_unknown_files(tmp_path):
    root, release = _project_fixture(tmp_path)
    unknown_files = {
        "scripts/credentials.json": '{"token": "do-not-package"}',
        "data/raw/orders.csv": "private raw row\n",
        "docs/user_behaviors.csv": "private raw row\n",
    }
    for relative, content in unknown_files.items():
        path = root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content, encoding="utf-8")

    archive_path, checksum_path, digest = build_package(tmp_path / "portfolio.zip", root=root)
    second_archive, _, second_digest = build_package(tmp_path / "portfolio-second.zip", root=root)

    assert checksum_path.read_text(encoding="utf-8").startswith(digest)
    assert second_digest == digest and second_archive.read_bytes() == archive_path.read_bytes()
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        assert f"{PACKAGE_ROOT}/README.md" in names
        assert f"{PACKAGE_ROOT}/bi_exports/current/manifest.json" in names
        assert f"{PACKAGE_ROOT}/PACKAGE_CONTENTS.sha256" in names
        assert f"{PACKAGE_ROOT}/PACKAGE_MANIFEST.json" in names
        assert not any(Path(name).name in {"orders.csv", "user_behaviors.csv"} for name in names)
        assert not any("/.venv/" in name or "/.tools/" in name or "/artifacts/" in name for name in names)
        manifest = json.loads(archive.read(f"{PACKAGE_ROOT}/bi_exports/current/manifest.json"))
        assert manifest["status"] == "success" and manifest["published"] is True
        info = archive.getinfo(f"{PACKAGE_ROOT}/bi_exports/current/manifest.json")
        assert stat.S_IFMT((info.external_attr >> 16) & 0xFFFF) == stat.S_IFREG

    kpi_path = release / "ads_executive_kpis.csv"
    rows = list(csv.DictReader(kpi_path.open(encoding="utf-8")))
    rows[0]["total_orders"] = "55"
    with kpi_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with pytest.raises(RuntimeError, match="total_orders"):
        build_package(tmp_path / "inconsistent.zip", root=root)


def test_unsupported_evidence_mode_is_blocked(tmp_path):
    root, _ = _project_fixture(tmp_path, mode="FULL")
    with pytest.raises(RuntimeError, match="only accepts"):
        build_package(tmp_path / "blocked.zip", root=root)


def test_custom_output_inside_project_remains_deterministic(tmp_path):
    root, _ = _project_fixture(tmp_path)
    destination = root / "scripts" / "portfolio.zip"
    first, _, first_digest = build_package(destination, root=root)
    first_bytes = first.read_bytes()
    second, _, second_digest = build_package(destination, root=root)
    assert second_digest == first_digest and second.read_bytes() == first_bytes
    with pytest.raises(RuntimeError, match=r"\.zip filename"):
        build_package(root / "README.md", root=root)


def test_output_and_checksum_symlinks_are_rejected_without_clobbering(tmp_path):
    root, _ = _project_fixture(tmp_path)
    target = tmp_path / "target.txt"; target.write_text("preserve me", encoding="utf-8")
    output_link = tmp_path / "linked.zip"; output_link.symlink_to(target)
    with pytest.raises(RuntimeError, match="output symlink"):
        build_package(output_link, root=root)
    assert target.read_text(encoding="utf-8") == "preserve me"
    output = tmp_path / "safe.zip"
    checksum_link = tmp_path / "safe.zip.sha256"; checksum_link.symlink_to(target)
    with pytest.raises(RuntimeError, match="checksum symlink"):
        build_package(output, root=root)


def test_publication_file_symlink_is_rejected(tmp_path):
    root, release = _project_fixture(tmp_path)
    outside = tmp_path / "outside.csv"; outside.write_text("private\ncontent\n", encoding="utf-8")
    published = release / "ads_daily_trend.csv"; published.unlink(); published.symlink_to(outside)
    with pytest.raises(RuntimeError, match="Published artifact must not be a symlink"):
        build_package(tmp_path / "portfolio.zip", root=root)


def test_legacy_five_column_contract_text_is_rejected(tmp_path):
    root, _ = _project_fixture(tmp_path)
    (root / "README.md").write_text(
        "Run the old pipeline with " + "DATA" + "_FILE=/tmp/UserBehavior.csv\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="legacy DATA_FILE command"):
        build_package(tmp_path / "portfolio.zip", root=root)
