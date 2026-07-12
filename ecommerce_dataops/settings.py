"""Filesystem and runtime settings for isolated pipeline runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunPaths:
    root: Path
    run_id: str

    @property
    def run_dir(self) -> Path:
        return self.root / "artifacts" / "runs" / self.run_id

    @property
    def warehouse_dir(self) -> Path:
        return self.run_dir / "spark-warehouse"

    @property
    def metastore_dir(self) -> Path:
        return self.run_dir / "metastore"

    @property
    def spark_local_dir(self) -> Path:
        return self.run_dir / "spark-local"

    @property
    def export_dir(self) -> Path:
        return self.run_dir / "exports"

    @property
    def manifest_path(self) -> Path:
        return self.run_dir / "manifest.json"

    @property
    def current_dir(self) -> Path:
        return self.root / "bi_exports" / "current"

    def create(self) -> None:
        for path in (
            self.run_dir,
            self.warehouse_dir,
            self.metastore_dir,
            self.spark_local_dir,
            self.export_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]

