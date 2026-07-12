"""Load the atomically published aggregate e-commerce ADS extracts."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "bi_exports" / "current"

FILE_CANDIDATES: dict[str, tuple[str, ...]] = {
    "kpis": ("ads_executive_kpis.csv",),
    "daily": ("ads_daily_trend.csv",),
    "funnel": ("ads_sequential_funnel.csv",),
    "categories": ("ads_category_performance.csv",),
    "hourly": ("ads_hourly_behavior.csv",),
    "segments": ("ads_customer_segments.csv",),
    "status": ("ads_order_status.csv",),
    "quality": ("ads_dataops_health.csv",),
}

NUMERIC_COLUMNS = {
    "total_orders",
    "ordering_customers",
    "paid_orders",
    "paid_customers",
    "completed_orders",
    "completed_customers",
    "all_order_amount",
    "paid_gmv",
    "completed_gmv",
    "paid_aov",
    "completed_aov",
    "completion_rate",
    "cancellation_refund_rate",
    "repeat_completed_customer_rate",
    "behavior_events",
    "behavior_users",
    "registered_users",
    "products",
    "categories",
    "quarantined_rows",
    "stage_order",
    "user_count",
    "previous_stage_conversion",
    "overall_conversion",
    "category_rank",
    "behavior_hour",
    "browse_events",
    "click_events",
    "favorite_events",
    "cart_events",
    "segment_order",
    "user_share",
    "status_order",
    "order_count",
    "order_share",
    "customer_count",
}

DATE_COLUMNS = {
    "run_date",
    "min_order_date",
    "max_order_date",
    "min_behavior_date",
    "max_behavior_date",
    "order_date",
    "checked_at",
}


@dataclass
class DashboardData:
    export_dir: Path
    manifest: dict[str, Any] = field(default_factory=dict)
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    source_files: dict[str, Path] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def table(self, name: str) -> pd.DataFrame:
        return self.tables.get(name, pd.DataFrame()).copy()

    @property
    def has_business_data(self) -> bool:
        return not self.table("kpis").empty


def _resolve_export_dir(export_dir: str | Path | None) -> Path:
    if export_dir is not None:
        return Path(export_dir).expanduser().resolve()
    override = os.getenv("ECOMMERCE_BI_EXPORT_DIR")
    return Path(override).expanduser().resolve() if override else DEFAULT_EXPORT_DIR


def publication_fingerprint(export_dir: str | Path | None = None) -> str:
    directory = _resolve_export_dir(export_dir)
    if not directory.is_dir():
        return f"{directory}:missing"
    parts = [str(directory)]
    for path in [directory / "manifest.json", *sorted(directory.glob("*.csv"))]:
        if path.is_file():
            stat = path.stat()
            parts.append(f"{path.name}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result.columns = [str(column).strip().lower() for column in result.columns]
    for column in NUMERIC_COLUMNS.intersection(result.columns):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    for column in DATE_COLUMNS.intersection(result.columns):
        result[column] = pd.to_datetime(result[column], errors="coerce")
    return result


def load_dashboard_data(export_dir: str | Path | None = None) -> DashboardData:
    directory = _resolve_export_dir(export_dir)
    bundle = DashboardData(export_dir=directory)
    if not directory.is_dir():
        bundle.errors.append("No published aggregate release found. Run the pipeline first.")
        return bundle

    manifest_path = directory / "manifest.json"
    if manifest_path.is_file():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                bundle.manifest = payload
            else:
                bundle.errors.append("manifest.json must contain one JSON object.")
        except (OSError, json.JSONDecodeError) as exc:
            bundle.errors.append(f"Cannot read manifest.json: {exc}")
    else:
        bundle.missing.append("manifest.json")

    for table_name, candidates in FILE_CANDIDATES.items():
        path = next((directory / name for name in candidates if (directory / name).is_file()), None)
        if path is None:
            bundle.missing.append(candidates[0])
            continue
        try:
            bundle.tables[table_name] = _normalize(pd.read_csv(path))
            bundle.source_files[table_name] = path
        except (OSError, UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            bundle.errors.append(f"Cannot read {path.name}: {exc}")
    return bundle


def manifest_value(manifest: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in manifest and manifest[key] not in (None, ""):
            return manifest[key]
    profile = manifest.get("data_profile")
    if isinstance(profile, dict):
        for key in keys:
            if key in profile and profile[key] not in (None, ""):
                return profile[key]
    return None
