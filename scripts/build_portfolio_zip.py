#!/usr/bin/env python3
"""Build a deterministic, raw-data-free portfolio archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.build_pages_site import _verify_publication


PACKAGE_ROOT = "ecommerce-dataops-portfolio"
DEFAULT_OUTPUT = ROOT / "dist" / "ecommerce-dataops-portfolio.zip"
FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
MAX_SOURCE_FILE_BYTES = 5 * 1024 * 1024

ALLOWED_SOURCE_FILES = {
    ".gitignore",
    ".github/workflows/ci.yml",
    ".github/workflows/pages.yml",
    "DATASET_NOTICE.md",
    "LICENSE",
    "LICENSE.md",
    "Makefile",
    "README.md",
    "REPRODUCE.md",
    "dashboard/__init__.py",
    "dashboard/app.py",
    "dashboard/data_loader.py",
    "dashboard/requirements.txt",
    "data/raw/README.md",
    "docs/architecture.md",
    "docs/data_lineage.md",
    "docs/full_data_runbook.md",
    "docs/interview_script_zh.md",
    "docs/jd_evidence_matrix.md",
    "docs/metric_dictionary.md",
    "docs/resume_bullets.md",
    "docs/showcase_and_recording_guide_zh.md",
    "pyproject.toml",
    "requirements.txt",
    "scripts/bootstrap_macos.sh",
    "scripts/build_portfolio_zip.py",
    "scripts/build_pages_site.py",
    "scripts/install_jdk.py",
    "scripts/recording_demo.sh",
    "sql/00_raw.sql",
    "sql/10_ods.sql",
    "sql/20_dwd.sql",
    "sql/30_dws_activity.sql",
    "sql/31_dws_users.sql",
    "sql/32_dws_categories.sql",
    "sql/40_ads.sql",
    "sql/90_quality.sql",
    "site/app.js",
    "site/index.html",
    "site/styles.css",
    "tableau/ACCEPTANCE_CHECKLIST.md",
    "tableau/BUILD_GUIDE.md",
    "tableau/CSV_DATA_DICTIONARY.md",
    "tableau/DASHBOARD_SPEC.md",
    "tableau/README.md",
    "ecommerce_dataops/__init__.py",
    "ecommerce_dataops/cli.py",
    "ecommerce_dataops/demo_data.py",
    "ecommerce_dataops/input_contract.py",
    "ecommerce_dataops/pipeline.py",
    "ecommerce_dataops/settings.py",
    "ecommerce_dataops/smoke.py",
    "ecommerce_dataops/spark_runtime.py",
    "ecommerce_dataops/sql_utils.py",
    "tests/integration/test_pipeline_e2e.py",
    "tests/ui/test_dashboard.py",
    "tests/unit/test_atomic_publish.py",
    "tests/unit/test_build_portfolio_zip.py",
    "tests/unit/test_build_pages_site.py",
    "tests/unit/test_demo_data.py",
    "tests/unit/test_input_contract.py",
    "tests/unit/test_install_jdk.py",
    "tests/unit/test_spark_runtime.py",
    "tests/unit/test_sql_utils.py",
}
SECRET_PATTERNS = {
    "private key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "OpenAI-style token": re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    "GitHub token": re.compile(rb"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "Slack token": re.compile(rb"xox[baprs]-[A-Za-z0-9-]{20,}"),
    "credential-bearing URL": re.compile(rb"https?://[^\s/:]+:[^\s/@]+@"),
}
STALE_PROJECT_PATTERNS = {
    "legacy DATA_FILE command": re.compile(rb"DATA_FILE\s*="),
    "legacy 5-field contract": re.compile(rb"five[- ]column", re.IGNORECASE),
    "legacy Chinese 5-field contract": re.compile("\u4e94\u5217".encode("utf-8")),
}
RAW_SOURCE_FILENAMES = {
    "users.csv",
    "products.csv",
    "orders.csv",
    "user_behaviors.csv",
    "user_features.csv",
    "product_features.csv",
    "UserBehavior.csv",
}
EXPECTED_PUBLICATION_FILES = {
    "manifest.json",
    "ads_dataops_health.csv",
    "ads_executive_kpis.csv",
    "ads_daily_trend.csv",
    "ads_sequential_funnel.csv",
    "ads_category_performance.csv",
    "ads_hourly_behavior.csv",
    "ads_customer_segments.csv",
    "ads_order_status.csv",
}


def _lexical_absolute(path: Path) -> Path:
    """Return an absolute path without following a pre-existing final symlink."""
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def _local_path_fragments(root: Path) -> tuple[bytes, ...]:
    candidates = {root.resolve(), Path.home().resolve()}
    return tuple(
        sorted(
            {
                os.fspath(path).encode("utf-8")
                for path in candidates
                if os.fspath(path) not in {"", os.path.sep}
            },
            key=len,
            reverse=True,
        )
    )


def _validate_source_payload(
    relative: Path,
    payload: bytes,
    *,
    forbidden_local_paths: tuple[bytes, ...] = (),
) -> None:
    if len(payload) > MAX_SOURCE_FILE_BYTES:
        raise RuntimeError(
            f"Curated source file is unexpectedly large ({len(payload):,} bytes): {relative}"
        )
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(payload):
            raise RuntimeError(f"Possible {label} found in curated source file: {relative}")
    for label, pattern in STALE_PROJECT_PATTERNS.items():
        if pattern.search(payload):
            raise RuntimeError(f"{label} found in curated source file: {relative}")
    for fragment in forbidden_local_paths:
        if fragment in payload:
            raise RuntimeError(f"Local absolute path found in packaged payload: {relative}")


def _validate_manifest_paths(value: object, *, location: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _validate_manifest_paths(child, location=f"{location}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _validate_manifest_paths(child, location=f"{location}[{index}]")
        return
    if not isinstance(value, str):
        return
    candidate = value.strip()
    if not candidate:
        return
    if PurePosixPath(candidate).is_absolute() or PureWindowsPath(candidate).is_absolute():
        raise RuntimeError(f"Published manifest contains an absolute path at {location}")


def _source_entries(
    root: Path = ROOT, *, excluded_paths: set[Path] | None = None
) -> dict[str, bytes]:
    source_root = root.resolve()
    forbidden_local_paths = _local_path_fragments(source_root)
    excluded = {_lexical_absolute(path) for path in (excluded_paths or set())}
    entries: dict[str, bytes] = {}
    for relative_text in sorted(ALLOWED_SOURCE_FILES):
        relative = Path(relative_text)
        source = source_root / relative
        if _lexical_absolute(source) in excluded:
            continue
        if source.is_symlink():
            raise RuntimeError(f"Unexpected source symlink: {relative}")
        if not source.exists():
            continue
        if not source.is_file():
            raise RuntimeError(f"Curated source path is not a regular file: {relative}")
        size = source.stat().st_size
        if size > MAX_SOURCE_FILE_BYTES:
            raise RuntimeError(
                f"Curated source file is unexpectedly large ({size:,} bytes): {relative}"
            )
        payload = source.read_bytes()
        _validate_source_payload(
            relative,
            payload,
            forbidden_local_paths=forbidden_local_paths,
        )
        entries[f"{PACKAGE_ROOT}/{relative.as_posix()}"] = payload
    return entries


def _publication_entries(*, root: Path = ROOT) -> tuple[dict[str, bytes], dict[str, object]]:
    source_root = root.resolve()
    current = source_root / "bi_exports" / "current"
    if not current.is_dir():
        raise RuntimeError("No published BI release found. Run `make demo` or `make full` first.")
    resolved = current.resolve(strict=True)
    releases = (source_root / "bi_exports" / "releases").resolve()
    if current.is_symlink() and releases != resolved and releases not in resolved.parents:
        raise RuntimeError(f"Published current path escapes bi_exports/releases: {resolved}")

    selected = resolved
    selected_resolved = selected.resolve(strict=True)
    checked_files: dict[str, Path] = {}
    missing: list[str] = []
    for name in sorted(EXPECTED_PUBLICATION_FILES):
        path = selected / name
        if path.is_symlink():
            raise RuntimeError(f"Published artifact must not be a symlink: {name}")
        if not path.is_file():
            missing.append(name)
            continue
        if path.resolve(strict=True).parent != selected_resolved:
            raise RuntimeError(f"Published artifact escapes selected release: {name}")
        checked_files[name] = path
    if missing:
        raise RuntimeError(f"Published release is incomplete: {', '.join(missing)}")

    manifest, _ = _verify_publication(selected)
    _validate_manifest_paths(manifest)

    entries: dict[str, bytes] = {}
    forbidden_local_paths = _local_path_fragments(source_root)
    for name in sorted(EXPECTED_PUBLICATION_FILES):
        payload = checked_files[name].read_bytes()
        _validate_source_payload(
            Path("bi_exports/current") / name,
            payload,
            forbidden_local_paths=forbidden_local_paths,
        )
        entries[f"{PACKAGE_ROOT}/bi_exports/current/{name}"] = payload
    return entries, manifest


def _generated_readme(manifest: dict[str, object]) -> bytes:
    run_id = str(manifest.get("run_id", "unknown"))
    data_mode = str(manifest.get("data_mode", "unknown"))
    text = f"""# Portable portfolio package

This archive contains the six-table e-commerce SQL + DataOps source, tests,
documentation, and compact published aggregate ADS extracts.

- Packaged run: `{run_id}`
- Data mode: `{data_mode}`
- Source status: `{manifest.get("source_status", "unknown")}`
- Raw six-table CSVs included: **no**
- Virtual environment or JDK included: **no**

On macOS with Python 3.9+ and network access:

```bash
make bootstrap
make demo
make test
make pages
make dashboard
```

`bi_exports/current/` is stored as a normal directory for ZIP portability. The
next successful pipeline run migrates it to the project's atomic release symlink.
See `README.md` and `REPRODUCE.md` for the full handoff.
"""
    return text.encode("utf-8")


def _contents_manifest(entries: dict[str, bytes]) -> bytes:
    lines = [f"{hashlib.sha256(payload).hexdigest()}  {name}" for name, payload in sorted(entries.items())]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _write_entry(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    executable = name.endswith(".sh") or name == f"{PACKAGE_ROOT}/scripts/build_portfolio_zip.py"
    mode = 0o755 if executable else 0o644
    info.external_attr = ((stat.S_IFREG | mode) & 0xFFFF) << 16
    archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def _validate_archive(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise RuntimeError("Archive contains duplicate entries")
        unsafe = [
            name
            for name in names
            if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
        ]
        if unsafe:
            raise RuntimeError(f"Archive contains unsafe paths: {unsafe}")
        symlinks = [
            info.filename
            for info in infos
            if stat.S_IFMT((info.external_attr >> 16) & 0xFFFF) == stat.S_IFLNK
        ]
        if symlinks:
            raise RuntimeError(f"Archive contains symlinks: {symlinks}")
        if not names or any(not name.startswith(f"{PACKAGE_ROOT}/") for name in names):
            raise RuntimeError("Archive entries must share one project root")
        forbidden = [
            name
            for name in names
            if "/.venv/" in name
            or "/.tools/" in name
            or "/artifacts/" in name
            or "/.git/" in name
            or Path(name).name in RAW_SOURCE_FILENAMES
            or "/.env" in name
        ]
        if forbidden:
            raise RuntimeError(f"Archive contains forbidden paths: {forbidden}")
        required = {
            f"{PACKAGE_ROOT}/README.md",
            f"{PACKAGE_ROOT}/Makefile",
            f"{PACKAGE_ROOT}/requirements.txt",
            f"{PACKAGE_ROOT}/bi_exports/current/manifest.json",
            f"{PACKAGE_ROOT}/PACKAGE_README.md",
            f"{PACKAGE_ROOT}/PACKAGE_MANIFEST.json",
            f"{PACKAGE_ROOT}/PACKAGE_CONTENTS.sha256",
        }
        missing = required - set(names)
        if missing:
            raise RuntimeError(f"Archive validation missing: {', '.join(sorted(missing))}")
        if archive.testzip() is not None:
            raise RuntimeError("Archive CRC validation failed")
        checksum_name = f"{PACKAGE_ROOT}/PACKAGE_CONTENTS.sha256"
        listed: dict[str, str] = {}
        for line in archive.read(checksum_name).decode("utf-8").splitlines():
            digest, name = line.split("  ", 1)
            listed[name] = digest
        expected_listed = set(names) - {checksum_name}
        if set(listed) != expected_listed:
            raise RuntimeError("Internal checksum manifest does not cover every payload exactly once")
        mismatched = [
            name
            for name, expected_digest in listed.items()
            if hashlib.sha256(archive.read(name)).hexdigest() != expected_digest
        ]
        if mismatched:
            raise RuntimeError(f"Internal checksum mismatch: {mismatched}")


def _atomic_write_text(path: Path, text: str) -> None:
    if path.is_symlink():
        raise RuntimeError(f"Refusing to replace checksum symlink: {path}")
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_package(
    output: Path = DEFAULT_OUTPUT,
    *,
    root: Path = ROOT,
) -> tuple[Path, Path, str]:
    destination = _lexical_absolute(output)
    if destination.suffix.lower() != ".zip":
        raise RuntimeError("Portfolio output must use a .zip filename")
    if destination.is_symlink():
        raise RuntimeError(f"Refusing to replace output symlink: {destination}")
    if destination.exists() and not destination.is_file():
        raise RuntimeError(f"Portfolio output is not a regular file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    checksum_path = destination.with_suffix(destination.suffix + ".sha256")
    if checksum_path.is_symlink():
        raise RuntimeError(f"Refusing to replace checksum symlink: {checksum_path}")

    entries = _source_entries(
        root,
        excluded_paths={destination, checksum_path},
    )
    publication, manifest = _publication_entries(root=root)
    entries.update(publication)
    entries[f"{PACKAGE_ROOT}/PACKAGE_README.md"] = _generated_readme(manifest)
    package_manifest = {
        "package_schema_version": 1,
        "source_run_id": manifest.get("run_id"),
        "data_mode": manifest.get("data_mode"),
        "source_status": manifest.get("source_status"),
        "raw_data_included": False,
        "git_commit": None,
        "git_commit_note": "Repository changes were not committed when this package was built.",
    }
    entries[f"{PACKAGE_ROOT}/PACKAGE_MANIFEST.json"] = (
        json.dumps(package_manifest, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    entries[f"{PACKAGE_ROOT}/PACKAGE_CONTENTS.sha256"] = _contents_manifest(entries)

    with tempfile.NamedTemporaryFile(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w") as archive:
            for name, payload in sorted(entries.items()):
                _write_entry(archive, name, payload)
        _validate_archive(temporary)
        os.replace(temporary, destination)
        os.chmod(destination, 0o644)
    finally:
        if temporary.exists():
            temporary.unlink()

    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    _atomic_write_text(checksum_path, f"{digest}  {destination.name}\n")
    return destination, checksum_path, digest


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    archive, checksum, digest = build_package(args.output)
    print(f"Portfolio ZIP: {_display_path(archive)}")
    print(f"SHA-256: {digest}")
    print(f"Checksum file: {_display_path(checksum)}")


if __name__ == "__main__":
    main()
