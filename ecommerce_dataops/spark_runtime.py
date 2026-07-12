"""Local Java and SparkSession configuration shared by the CLI and tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def configure_java(root: Path) -> None:
    java_home_file = root / ".tools" / "java_home"
    if java_home_file.exists():
        java_home = java_home_file.read_text(encoding="utf-8").strip()
        if java_home and (Path(java_home) / "bin" / "java").is_file():
            os.environ["JAVA_HOME"] = java_home
            os.environ["PATH"] = f"{Path(java_home) / 'bin'}:{os.environ.get('PATH', '')}"
    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)


def create_spark_session(
    root: Path,
    warehouse_dir: Path,
    metastore_dir: Path,
    spark_local_dir: Path,
    *,
    app_name: str,
    shuffle_partitions: int,
):
    configure_java(root)
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:
        raise RuntimeError("PySpark is not installed. Run: make bootstrap") from exc

    for path in (warehouse_dir, metastore_dir, spark_local_dir):
        path.mkdir(parents=True, exist_ok=True)

    # Derby creates the database directory itself. Point it at a child that does
    # not exist yet while keeping the parent available for run isolation.
    metastore_database = metastore_dir / "metastore_db"
    connection_url = f"jdbc:derby:;databaseName={metastore_database.resolve()};create=true"
    spark = (
        SparkSession.builder.master("local[2]")
        .appName(app_name)
        .config("spark.ui.enabled", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
        .config("spark.sql.session.timeZone", "Asia/Shanghai")
        .config("spark.sql.warehouse.dir", warehouse_dir.resolve().as_uri())
        .config("spark.local.dir", str(spark_local_dir.resolve()))
        .config("spark.hadoop.javax.jdo.option.ConnectionURL", connection_url)
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .config("spark.sql.adaptive.enabled", "true")
        .enableHiveSupport()
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark
