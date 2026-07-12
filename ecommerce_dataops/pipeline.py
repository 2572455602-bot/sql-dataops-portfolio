"""SparkSQL pipeline orchestration, quality gating, manifests, and atomic exports."""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from ecommerce_dataops.input_contract import (
    ContractError,
    DatasetInspection,
    EXPECTED_SCHEMAS,
    inspect_dataset,
)
from ecommerce_dataops.settings import RunPaths
from ecommerce_dataops.spark_runtime import create_spark_session
from ecommerce_dataops.sql_utils import discover_sql_files, execute_sql_files, sql_bundle_sha256


class PipelineError(RuntimeError):
    """Base class for pipeline failures that must not publish candidate data."""


class QualityGateError(PipelineError):
    """Raised when one or more critical DataOps checks fail."""


EXPORT_TABLES: dict[str, str] = {
    "ads_executive_kpis": "ads_executive_kpis.csv",
    "ads_daily_trend": "ads_daily_trend.csv",
    "ads_sequential_funnel": "ads_sequential_funnel.csv",
    "ads_category_performance": "ads_category_performance.csv",
    "ads_hourly_behavior": "ads_hourly_behavior.csv",
    "ads_customer_segments": "ads_customer_segments.csv",
    "ads_order_status": "ads_order_status.csv",
    "ads_dataops_health": "ads_dataops_health.csv",
}

EXPORT_SORT_KEYS: dict[str, list[str]] = {
    "ads_daily_trend": ["order_date"],
    "ads_sequential_funnel": ["stage_order"],
    "ads_category_performance": ["category_rank"],
    "ads_hourly_behavior": ["behavior_hour"],
    "ads_customer_segments": ["segment_order"],
    "ads_order_status": ["status_order"],
    "ads_dataops_health": ["check_name"],
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _run_id(data_mode: str) -> str:
    timestamp = _utc_now().strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{data_mode.lower()}-{uuid.uuid4().hex[:8]}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _sync_committed_run_manifest(paths: RunPaths, manifest: dict[str, Any]) -> None:
    """Best-effort copy after the publication commit point.

    The manifest inside ``bi_exports/current`` is authoritative once the
    symlink switch succeeds. A secondary run-artifact write must not reverse
    that committed publication into a reported failure.
    """
    try:
        _write_json(paths.manifest_path, manifest)
    except Exception as exc:  # noqa: BLE001 - commit-point safety is intentional.
        manifest["run_manifest_sync_warning"] = f"{type(exc).__name__}: {exc}"


def _input_manifest(inspection: DatasetInspection) -> dict[str, Any]:
    return {
        "directory_name": inspection.root.name,
        "size_bytes": inspection.size_bytes,
        "combined_sha256": inspection.combined_sha256,
        "row_count": inspection.row_count,
        "preflight_sampled_rows": inspection.sampled_rows,
        "files": {
            name: {
                "size_bytes": item.size_bytes,
                "sha256": item.sha256,
                "row_count": item.row_count,
                "sampled_rows": item.sampled_rows,
            }
            for name, item in sorted(inspection.files.items())
        },
        "raw_files_committed": False,
    }


def _register_raw_tables(spark: Any, inspection: DatasetInspection, ingested_at: datetime) -> list[str]:
    from pyspark.sql import functions as F

    registered: list[str] = []
    for filename, columns in EXPECTED_SCHEMAS.items():
        stem = Path(filename).stem
        table_name = f"raw_{stem}_external"
        view_name = f"raw_{stem}_raw"
        escaped_path = inspection.files[filename].path.as_uri().replace("'", "''")
        schema_sql = ",\n            ".join(
            [*(f"`{column}` STRING" for column in columns), "_corrupt_record STRING"]
        )
        spark.sql(f"DROP TABLE IF EXISTS {table_name}")
        spark.sql(
            f"""
            CREATE TABLE {table_name} (
                {schema_sql}
            )
            USING CSV
            OPTIONS (
                path '{escaped_path}',
                header 'true',
                mode 'PERMISSIVE',
                columnNameOfCorruptRecord '_corrupt_record'
            )
            """
        )
        projection = (
            spark.table(table_name)
            .withColumn("_source_file", F.lit(filename))
            .withColumn("_ingested_at", F.lit(ingested_at))
        )
        projection.createOrReplaceTempView(view_name)
        registered.append(table_name)
    return registered


def _table_exists(spark: Any, table_name: str) -> bool:
    return bool(spark.catalog.tableExists(table_name))


def _collect_quality(spark: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not _table_exists(spark, "ops_data_quality_results"):
        raise PipelineError("Quality SQL did not create ops_data_quality_results")
    quality_rows = [row.asDict(recursive=True) for row in spark.table("ops_data_quality_results").collect()]
    if not quality_rows:
        raise PipelineError("Quality SQL returned no checks")
    blocking = [
        row
        for row in quality_rows
        if str(row.get("severity", "")).lower() == "critical"
        and str(row.get("check_status", "")).lower() != "pass"
    ]
    return quality_rows, blocking


def _export_ads(
    spark: Any,
    export_dir: Path,
    data_mode: str,
    source_status: str,
) -> dict[str, int]:
    export_dir.mkdir(parents=True, exist_ok=True)
    row_counts: dict[str, int] = {}
    for table_name, file_name in EXPORT_TABLES.items():
        if not _table_exists(spark, table_name):
            raise PipelineError(f"Required ADS table is missing: {table_name}")
        dataset = spark.table(table_name)
        sort_keys = [key for key in EXPORT_SORT_KEYS.get(table_name, []) if key in dataset.columns]
        if sort_keys:
            dataset = dataset.orderBy(*sort_keys)
        frame = dataset.toPandas()
        if table_name == "ads_executive_kpis":
            frame["run_date"] = date.today().isoformat()
            frame["data_mode"] = data_mode.upper()
            frame["source_status"] = source_status.upper()
            preferred = ["run_date", "data_mode", "source_status"] + [
                column
                for column in frame.columns
                if column not in {"run_date", "data_mode", "source_status"}
            ]
            frame = frame[preferred]
        destination = export_dir / file_name
        frame.to_csv(destination, index=False)
        row_counts[table_name] = len(frame)
    return row_counts


def _atomic_publish(paths: RunPaths, manifest: dict[str, Any]) -> None:
    """Publish an immutable release with one atomic ``current`` symlink switch."""
    parent = paths.current_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    releases = parent / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    candidate = parent / f".candidate-{paths.run_id}"
    release = releases / paths.run_id
    pointer = parent / f".current-link-{paths.run_id}"
    legacy = releases / f"_legacy-{paths.run_id}"
    if candidate.exists():
        shutil.rmtree(candidate)
    if pointer.exists() or pointer.is_symlink():
        pointer.unlink()
    if release.exists():
        raise PipelineError(f"Release path already exists: {release}")

    shutil.copytree(paths.export_dir, candidate)
    published_manifest = dict(manifest)
    published_manifest["published"] = True
    _write_json(candidate / "manifest.json", published_manifest)
    os.replace(candidate, release)
    os.symlink(os.path.relpath(release, parent), pointer, target_is_directory=True)

    moved_legacy = False
    try:
        # Convert the repository's initial physical snapshot once. After that,
        # every publication is a single atomic symlink replacement.
        if paths.current_dir.exists() and not paths.current_dir.is_symlink():
            os.replace(paths.current_dir, legacy)
            moved_legacy = True
        os.replace(pointer, paths.current_dir)
    except Exception:
        if moved_legacy and legacy.exists() and not paths.current_dir.exists():
            os.replace(legacy, paths.current_dir)
        if pointer.exists() or pointer.is_symlink():
            pointer.unlink()
        if release.exists():
            shutil.rmtree(release)
        raise
    if moved_legacy and legacy.exists():
        try:
            shutil.rmtree(legacy)
        except OSError:
            # The current pointer has already committed. Cleanup must never
            # turn a successful atomic switch into a reported failure.
            pass


def _dataset_stats(spark: Any) -> dict[str, Any]:
    from pyspark.sql import functions as F

    raw_tables = {
        "users": "raw_users_contract",
        "products": "raw_products_contract",
        "orders": "raw_orders_contract",
        "user_behaviors": "raw_user_behaviors_contract",
        "user_features": "raw_user_features_contract",
        "product_features": "raw_product_features_contract",
    }
    valid_tables = {
        "users": "ods_users_valid",
        "products": "ods_products_valid",
        "orders": "ods_orders_valid",
        "user_behaviors": "ods_user_behaviors_valid",
        "user_features": "ods_user_features_valid",
        "product_features": "ods_product_features_valid",
    }
    dwd_tables = {
        "users": "dwd_dim_user",
        "products": "dwd_dim_product",
        "orders": "dwd_fact_order",
        "user_behaviors": "dwd_fact_behavior",
        "user_features": "dwd_feature_snapshot_user",
        "product_features": "dwd_feature_snapshot_product",
    }
    raw_counts = {name: spark.table(table).count() for name, table in raw_tables.items()}
    valid_counts = {name: spark.table(table).count() for name, table in valid_tables.items()}
    dwd_counts = {name: spark.table(table).count() for name, table in dwd_tables.items()}
    quarantine_rows = spark.table("ods_quarantine").count()
    order_dates = spark.table("dwd_fact_order").agg(
        F.min("order_date").alias("min_date"), F.max("order_date").alias("max_date")
    ).first()
    behavior_dates = spark.table("dwd_fact_behavior").agg(
        F.min("behavior_date").alias("min_date"), F.max("behavior_date").alias("max_date")
    ).first()
    minimums = [row["min_date"] for row in (order_dates, behavior_dates) if row and row["min_date"]]
    maximums = [row["max_date"] for row in (order_dates, behavior_dates) if row and row["max_date"]]
    return {
        "raw_rows": sum(raw_counts.values()),
        "valid_rows": sum(valid_counts.values()),
        "quarantine_rows": quarantine_rows,
        "dwd_rows": sum(dwd_counts.values()),
        "raw_table_rows": raw_counts,
        "valid_table_rows": valid_counts,
        "dwd_table_rows": dwd_counts,
        "min_event_date": min(minimums) if minimums else None,
        "max_event_date": max(maximums) if maximums else None,
    }


def run_pipeline(
    project_root: Path,
    input_dir: Path,
    data_mode: str,
    *,
    runtime_root: Path | None = None,
    publish: bool = True,
) -> dict[str, Any]:
    """Build a candidate warehouse and publish exports only after critical checks pass."""
    normalized_mode = data_mode.lower()
    if normalized_mode not in {"demo", "portfolio"}:
        raise ValueError(f"Unsupported data mode: {data_mode}")

    source_root = project_root.resolve()
    state_root = (runtime_root or project_root).resolve()
    run_id = _run_id(normalized_mode)
    paths = RunPaths(state_root, run_id)
    paths.create()
    started_at = _utc_now()
    start_clock = time.monotonic()
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "project": "ecommerce_six_table_dataops",
        "data_mode": normalized_mode.upper(),
        "source_status": "SYNTHETIC_FIXTURE" if normalized_mode == "demo" else "UNVERIFIED",
        "dataset_profile": "ecommerce_six_table_v1",
        "status": "running",
        "started_at": started_at.isoformat(),
        "published": False,
    }
    spark = None

    try:
        inspection = inspect_dataset(input_dir)
        manifest["input"] = _input_manifest(inspection)
        sql_files = discover_sql_files(source_root / "sql")
        manifest["sql"] = {
            "bundle_sha256": sql_bundle_sha256(sql_files),
            "files": [path.relative_to(source_root).as_posix() for path in sql_files],
        }

        spark = create_spark_session(
            source_root,
            paths.warehouse_dir,
            paths.metastore_dir,
            paths.spark_local_dir,
            app_name=f"ecommerce-dataops-{run_id}",
            shuffle_partitions=8,
        )
        manifest["spark_version"] = spark.version
        raw_tables = _register_raw_tables(spark, inspection, started_at)
        manifest["raw"] = {
            "external_tables": raw_tables,
            "format": "CSV",
            "header": True,
        }
        execution_log = execute_sql_files(spark, sql_files)
        for entry in execution_log:
            entry["file"] = Path(str(entry["file"])).relative_to(source_root).as_posix()
        manifest["sql"]["executed_statements"] = execution_log

        quality_rows, blocking = _collect_quality(spark)
        manifest["quality"] = {
            "total_checks": len(quality_rows),
            "passed_checks": sum(str(row.get("check_status", "")).lower() == "pass" for row in quality_rows),
            "failed_checks": sum(str(row.get("check_status", "")).lower() == "fail" for row in quality_rows),
            "warning_checks": sum(str(row.get("check_status", "")).lower() == "warn" for row in quality_rows),
            "blocking_checks": [row.get("check_name") for row in blocking],
            "status": "fail" if blocking else "pass",
        }
        manifest["data_profile"] = _dataset_stats(spark)
        if blocking:
            names = ", ".join(str(row.get("check_name")) for row in blocking)
            raise QualityGateError(f"Critical quality checks failed: {names}")

        export_counts = _export_ads(
            spark,
            paths.export_dir,
            normalized_mode,
            str(manifest["source_status"]),
        )
        if any(count == 0 for count in export_counts.values()):
            empty = [table for table, count in export_counts.items() if count == 0]
            raise QualityGateError(f"Required ADS exports are empty: {', '.join(empty)}")
        manifest["exports"] = export_counts
        manifest["status"] = "success"
        manifest["finished_at"] = _utc_now().isoformat()
        manifest["duration_seconds"] = round(time.monotonic() - start_clock, 3)
        manifest["published"] = False
        _write_json(paths.manifest_path, manifest)
        if publish:
            _atomic_publish(paths, manifest)
            manifest["published"] = True
            _sync_committed_run_manifest(paths, manifest)
        return manifest
    except Exception as exc:
        if "input" not in manifest and isinstance(exc, ContractError) and exc.inspection is not None:
            manifest["input"] = _input_manifest(exc.inspection)
        manifest["status"] = "failed"
        manifest["error_type"] = type(exc).__name__
        manifest["error"] = str(exc)
        manifest["finished_at"] = _utc_now().isoformat()
        manifest["duration_seconds"] = round(time.monotonic() - start_clock, 3)
        manifest["published"] = False
        _write_json(paths.manifest_path, manifest)
        raise
    finally:
        if spark is not None:
            spark.stop()
