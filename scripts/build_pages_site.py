#!/usr/bin/env python3
"""Build the recruiter-facing static GitHub Pages artifact from verified ADS evidence."""

from __future__ import annotations

import argparse
import csv
from html import escape
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TEMPLATE_DIR = ROOT / "site"
DEFAULT_EXPORT_DIR = ROOT / "bi_exports" / "current"
DEFAULT_OUTPUT = ROOT / "dist" / "pages"
DEFAULT_LIVE_DASHBOARD_URL = (
    "https://sql-dataops-portfolio-bzzv3wfoclo7er2a2aqudj.streamlit.app/"
)


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected one JSON object: {path}")
    return payload


def _read_first_csv_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle), None)
    if row is None:
        raise RuntimeError(f"Published KPI extract is empty: {path}")
    return row


def _validated_https_url(value: str | None, *, label: str) -> str | None:
    if not value:
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError(f"{label} must be an absolute https:// URL")
    return value.strip()


def _format_integer(value: object) -> str:
    numeric = float(str(value))
    if not numeric.is_integer() or numeric < 0:
        raise RuntimeError(f"Public count must be a non-negative integer, got: {value}")
    return f"{int(numeric):,}"


def _format_rate(value: object) -> str:
    numeric = float(str(value))
    if not 0 <= numeric <= 1:
        raise RuntimeError(f"Public rate must be between 0 and 1, got: {value}")
    return f"{numeric:.1%}"


def _format_sample_amount(value: object) -> str:
    numeric = float(str(value))
    if numeric < 0:
        raise RuntimeError(f"Public sample amount must be non-negative, got: {value}")
    if numeric >= 1_000_000:
        return f"{numeric / 1_000_000:.2f}M"
    if numeric >= 1_000:
        return f"{numeric / 1_000:.1f}K"
    return f"{numeric:,.2f}"


def _repository_url(explicit: str | None) -> str | None:
    if explicit:
        return _validated_https_url(explicit, label="Repository URL")
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    if repository and repository.count("/") == 1:
        return f"https://github.com/{repository}"
    return None


def _verify_publication(export_dir: Path) -> tuple[dict[str, object], dict[str, str]]:
    if not export_dir.is_dir():
        raise RuntimeError("No published BI evidence found. Run `make demo` first.")
    manifest_path = export_dir / "manifest.json"
    kpi_path = export_dir / "ads_executive_kpis.csv"
    if manifest_path.is_symlink() or kpi_path.is_symlink():
        raise RuntimeError("Published evidence files must not be symlinks")
    if not manifest_path.is_file() or not kpi_path.is_file():
        raise RuntimeError("Published evidence is missing manifest.json or ads_executive_kpis.csv")

    manifest = _read_json(manifest_path)
    mode = str(manifest.get("data_mode", "")).upper()
    quality = manifest.get("quality")
    if not isinstance(quality, dict):
        raise RuntimeError("Published manifest has no quality summary")
    if manifest.get("status") != "success" or manifest.get("published") is not True:
        raise RuntimeError("Only a successful published run can build the public site")
    total_checks = int(quality.get("total_checks", -1))
    passed_checks = int(quality.get("passed_checks", -1))
    failed_checks = int(quality.get("failed_checks", -1))
    warning_checks = int(quality.get("warning_checks", 0))
    if min(total_checks, passed_checks, failed_checks, warning_checks) < 0:
        raise RuntimeError("Public quality counts must be non-negative integers")
    if passed_checks + failed_checks + warning_checks != total_checks:
        raise RuntimeError("Public quality counts do not reconcile to total_checks")
    if quality.get("status") != "pass" or failed_checks != 0:
        raise RuntimeError("Public site build requires a passing quality gate")
    if mode not in {"DEMO", "PORTFOLIO"}:
        raise RuntimeError(
            "Public Pages only accepts DEMO or source-unverified PORTFOLIO evidence."
        )
    source_status = str(manifest.get("source_status", "")).upper()
    allowed_source_status = {
        "DEMO": "SYNTHETIC_FIXTURE",
        "PORTFOLIO": "UNVERIFIED",
    }
    if source_status != allowed_source_status[mode]:
        raise RuntimeError("Public data mode and source-status disclosure do not agree")
    kpis = _read_first_csv_row(kpi_path)
    profile = manifest.get("data_profile")
    if not isinstance(profile, dict):
        raise RuntimeError("Published manifest has no data profile")
    profile_counts: dict[str, int] = {}
    for name in ("raw_rows", "valid_rows", "quarantine_rows", "dwd_rows"):
        value = profile.get(name, -1)
        _format_integer(value)
        profile_counts[name] = int(float(str(value)))
    if min(profile_counts.values()) < 0:
        raise RuntimeError("Public data profile counts must be non-negative")
    if profile_counts["raw_rows"] != profile_counts["valid_rows"] + profile_counts["quarantine_rows"]:
        raise RuntimeError("Public RAW rows do not reconcile to valid plus quarantine rows")
    if profile_counts["valid_rows"] != profile_counts["dwd_rows"]:
        raise RuntimeError("Public valid and DWD row counts do not reconcile")

    for name in (
        "total_orders",
        "completed_orders",
        "completed_customers",
        "behavior_events",
        "registered_users",
        "products",
    ):
        _format_integer(kpis[name])
    total_orders = int(float(str(kpis["total_orders"])))
    completed_orders = int(float(str(kpis["completed_orders"])))
    completed_customers = int(float(str(kpis["completed_customers"])))
    completion_rate = float(str(kpis["completion_rate"]))
    _format_rate(completion_rate)
    _format_sample_amount(kpis["completed_gmv"])
    if completed_orders > total_orders:
        raise RuntimeError("Completed orders cannot exceed total valid orders")
    if completed_customers > completed_orders:
        raise RuntimeError("Completed customers cannot exceed completed orders")
    if total_orders and abs(completion_rate - completed_orders / total_orders) > 0.0001:
        raise RuntimeError(
            "Public completion_rate does not reconcile with total_orders and completed_orders"
        )
    valid_table_rows = profile.get("valid_table_rows")
    if not isinstance(valid_table_rows, dict):
        raise RuntimeError("Published manifest has no per-table valid row profile")
    if total_orders != int(valid_table_rows.get("orders", -1)):
        raise RuntimeError("Public total_orders does not reconcile to valid order rows")
    if int(float(str(kpis["behavior_events"]))) != int(valid_table_rows.get("user_behaviors", -1)):
        raise RuntimeError("Public behavior_events does not reconcile to valid behavior rows")
    return manifest, kpis


def build_pages_site(
    output: Path = DEFAULT_OUTPUT,
    *,
    export_dir: Path = DEFAULT_EXPORT_DIR,
    repository_url: str | None = None,
    live_dashboard_url: str | None = None,
) -> Path:
    manifest, kpis = _verify_publication(export_dir.resolve())
    quality = manifest["quality"]
    if not isinstance(quality, dict):
        raise RuntimeError("Published manifest has no quality summary")
    profile = manifest.get("data_profile")
    if not isinstance(profile, dict):
        raise RuntimeError("Published manifest has no data profile")

    mode = str(manifest["data_mode"]).upper()
    repo_url = _repository_url(repository_url)
    live_url = _validated_https_url(
        live_dashboard_url or os.getenv("LIVE_DASHBOARD_URL") or DEFAULT_LIVE_DASHBOARD_URL,
        label="Live dashboard URL",
    )
    data_notice = (
        "Demo data only. Raw files are not included."
        if mode == "DEMO"
        else "Source unverified. Raw files are not included."
    )
    replacements = {
        "DATA_MODE": mode,
        "SOURCE_BADGE": "DEMO DATA" if mode == "DEMO" else "UNVERIFIED DATA",
        "DATA_NOTICE": data_notice,
        "TOTAL_ORDERS": _format_integer(kpis["total_orders"]),
        "SAMPLE_AMOUNT": _format_sample_amount(kpis["completed_gmv"]),
        "CUSTOMERS": _format_integer(kpis["completed_customers"]),
        "COMPLETION_RATE": _format_rate(kpis["completion_rate"]),
        "REPOSITORY_URL": repo_url or "#main",
        "REPOSITORY_BUTTON_CLASS": "" if repo_url else "is-disabled",
        "REPOSITORY_BUTTON_LABEL": "打开 GitHub 源码" if repo_url else "GitHub 源码待发布",
        "LIVE_DASHBOARD_URL": live_url or "#main",
        "LIVE_BUTTON_CLASS": "" if live_url else "is-disabled",
        "LIVE_BUTTON_LABEL": "打开在线 Dashboard" if live_url else "在线 Dashboard 待发布",
    }

    template = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
    for key, value in replacements.items():
        template = template.replace("{{" + key + "}}", escape(value, quote=True))
    if "{{" in template or "}}" in template:
        raise RuntimeError("Static site template still contains unresolved placeholders")

    destination = Path(os.path.abspath(os.fspath(output.expanduser())))
    if destination.is_symlink():
        raise RuntimeError(f"Refusing to replace Pages output symlink: {destination}")
    destination_real = destination.resolve(strict=False)
    allowed_roots = (
        (ROOT / "dist").resolve(),
        (ROOT / "_site").resolve(),
        Path(tempfile.gettempdir()).resolve(),
    )
    try:
        project_relative = destination_real.relative_to(ROOT.resolve())
    except ValueError:
        project_relative = None
    is_pytest_temp = bool(
        project_relative
        and project_relative.parts
        and project_relative.parts[0].startswith(".pytest-tmp")
    )
    if not is_pytest_temp and not any(
        destination_real == base or base in destination_real.parents for base in allowed_roots
    ):
        raise RuntimeError(
            "Pages output must stay under dist/, _site/, a project pytest temp directory, "
            "or the system temp directory"
        )
    for protected in (TEMPLATE_DIR.resolve(), (ROOT / "dashboard").resolve()):
        if destination == protected or protected in destination.parents:
            raise RuntimeError("Refusing to overwrite project source with a generated Pages artifact")
    if destination.exists():
        markers = (
            destination / ".ecommerce-pages-artifact",
            destination / ".taobao-pages-artifact",
        )
        if not destination.is_dir() or not any(marker.is_file() for marker in markers):
            raise RuntimeError(f"Refusing to delete unrecognized Pages output: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent)
    )
    try:
        (temporary / "index.html").write_text(template, encoding="utf-8")
        shutil.copy2(TEMPLATE_DIR / "styles.css", temporary / "styles.css")
        shutil.copy2(TEMPLATE_DIR / "app.js", temporary / "app.js")
        (temporary / ".nojekyll").write_text("", encoding="utf-8")
        (temporary / ".ecommerce-pages-artifact").write_text("generated\n", encoding="utf-8")
        build_info = {
            "source_run_id": manifest["run_id"],
            "data_mode": mode,
            "quality_status": quality["status"],
            "repository_url": repo_url,
            "live_dashboard_url": live_url,
            "source_status": manifest["source_status"],
            "raw_data_included": False,
        }
        (temporary / "build-info.json").write_text(
            json.dumps(build_info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if destination.exists():
            shutil.rmtree(destination)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    parser.add_argument("--repository-url")
    parser.add_argument("--live-dashboard-url")
    args = parser.parse_args()
    output = build_pages_site(
        args.output,
        export_dir=args.export_dir,
        repository_url=args.repository_url,
        live_dashboard_url=args.live_dashboard_url,
    )
    print(f"GitHub Pages artifact: {output}")


if __name__ == "__main__":
    main()
