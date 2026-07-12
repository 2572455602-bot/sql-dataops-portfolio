"""Preflight contract for the six-table e-commerce portfolio dataset."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path


EXPECTED_SCHEMAS: dict[str, tuple[str, ...]] = {
    "users.csv": (
        "user_id",
        "age",
        "gender",
        "province",
        "city",
        "registration_date",
        "member_level",
        "account_balance",
        "credit_score",
    ),
    "products.csv": (
        "product_id",
        "product_name",
        "category",
        "brand",
        "price",
        "sales_count",
    ),
    "orders.csv": (
        "order_id",
        "user_id",
        "product_id",
        "quantity",
        "order_date",
        "order_status",
        "payment_method",
        "unit_price",
        "total_amount",
        "discount",
        "actual_payment",
        "delivery_date",
        "receive_date",
        "review_score",
        "review_content",
    ),
    "user_behaviors.csv": (
        "behavior_id",
        "user_id",
        "product_id",
        "behavior_type",
        "behavior_time",
        "duration_seconds",
    ),
    "user_features.csv": (
        "user_id",
        "total_spent",
        "order_count",
        "completed_orders",
        "avg_order_amount",
        "browse_count",
        "click_count",
        "favorite_count",
        "cart_count",
        "days_since_last_order",
        "order_frequency",
        "repurchase_indicator",
        "purchase_intent",
        "consumption_level",
        "member_level_score",
    ),
    "product_features.csv": (
        "product_id",
        "total_revenue",
        "total_sales",
        "completed_count",
        "cancel_count",
        "加购_count",
        "收藏_count",
        "浏览_count",
        "点击_count",
        "conversion_rate",
        "avg_review_score",
        "popularity_score",
    ),
}


class ContractError(ValueError):
    """Raised when an input directory cannot satisfy the six-table contract."""

    def __init__(self, message: str, inspection: "DatasetInspection | None" = None) -> None:
        super().__init__(message)
        self.inspection = inspection


@dataclass(frozen=True)
class FileInspection:
    path: Path
    size_bytes: int
    sha256: str
    row_count: int
    sampled_rows: int


@dataclass(frozen=True)
class DatasetInspection:
    root: Path
    files: dict[str, FileInspection]
    combined_sha256: str

    @property
    def size_bytes(self) -> int:
        return sum(item.size_bytes for item in self.files.values())

    @property
    def row_count(self) -> int:
        return sum(item.row_count for item in self.files.values())

    @property
    def sampled_rows(self) -> int:
        return sum(item.sampled_rows for item in self.files.values())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_dataset(path: Path, sample_limit: int = 2000) -> DatasetInspection:
    """Validate filenames, exact headers, row width, and file fingerprints."""

    root = path.expanduser().resolve()
    if not root.is_dir():
        raise ContractError(f"Dataset directory does not exist: {root}")

    inspected: dict[str, FileInspection] = {}
    combined = hashlib.sha256()
    for filename, expected_header in EXPECTED_SCHEMAS.items():
        source = root / filename
        if source.is_symlink():
            raise ContractError(f"Dataset file must not be a symlink: {filename}")
        if not source.is_file():
            raise ContractError(f"Required dataset file is missing: {filename}")
        size_bytes = source.stat().st_size
        digest = _sha256(source)
        if size_bytes == 0:
            raise ContractError(f"Dataset file is empty: {filename}")

        row_count = 0
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = tuple(next(reader, ()))
            if header != expected_header:
                raise ContractError(
                    f"{filename} header does not match the required contract; "
                    f"expected {len(expected_header)} columns"
                )
            for line_number, row in enumerate(reader, start=2):
                row_count += 1
                if len(row) != len(expected_header):
                    raise ContractError(
                        f"{filename} row {line_number} has {len(row)} columns; "
                        f"expected {len(expected_header)}"
                    )
        if row_count == 0:
            raise ContractError(f"Dataset file has no data rows: {filename}")
        inspection = FileInspection(
            path=source,
            size_bytes=size_bytes,
            sha256=digest,
            row_count=row_count,
            sampled_rows=min(row_count, sample_limit),
        )
        inspected[filename] = inspection
        combined.update(filename.encode("utf-8"))
        combined.update(b"\0")
        combined.update(digest.encode("ascii"))
        combined.update(b"\0")

    return DatasetInspection(root=root, files=inspected, combined_sha256=combined.hexdigest())
