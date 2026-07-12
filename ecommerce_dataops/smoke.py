"""Environment smoke test for Java, Spark SQL, Hive metastore, and Parquet."""

from __future__ import annotations

import tempfile
from pathlib import Path

from ecommerce_dataops.settings import project_root
from ecommerce_dataops.spark_runtime import create_spark_session


def main() -> None:
    root = project_root()
    with tempfile.TemporaryDirectory(prefix="ecommerce-spark-smoke-") as temporary:
        temp = Path(temporary)
        spark = create_spark_session(
            root,
            temp / "warehouse",
            temp / "metastore",
            temp / "spark-local",
            app_name="ecommerce-dataops-smoke",
            shuffle_partitions=2,
        )
        try:
            spark.sql("CREATE TABLE smoke_numbers USING PARQUET AS SELECT 1 AS value UNION ALL SELECT 2")
            count = spark.sql("SELECT COUNT(*) AS row_count FROM smoke_numbers").first()["row_count"]
            parquet_path = temp / "parquet-check"
            spark.table("smoke_numbers").write.mode("overwrite").parquet(str(parquet_path))
            parquet_count = spark.read.parquet(str(parquet_path)).count()
            if count != 2 or parquet_count != 2:
                raise RuntimeError(f"Smoke test reconciliation failed: hive={count}, parquet={parquet_count}")
            print(f"Spark/Hive/Parquet smoke test passed (Spark {spark.version}).")
        finally:
            spark.stop()


if __name__ == "__main__":
    main()
