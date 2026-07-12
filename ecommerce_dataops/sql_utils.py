"""SQL discovery, checksums, and a small SparkSQL-aware statement splitter."""

from __future__ import annotations

import hashlib
from pathlib import Path


SQL_PHASES = ("ods", "dwd", "dws", "ads", "quality")


def discover_sql_files(sql_root: Path) -> list[Path]:
    root_files = sorted(sql_root.glob("*.sql"))
    if root_files:
        return root_files
    files: list[Path] = []
    for phase in SQL_PHASES:
        phase_dir = sql_root / phase
        if phase_dir.exists():
            files.extend(sorted(phase_dir.glob("*.sql")))
    if not files:
        raise FileNotFoundError(f"No SQL files found under {sql_root}")
    return files


def sql_bundle_sha256(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(path.parents[1]).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def split_sql(text: str) -> list[str]:
    """Split statements while respecting strings, identifiers, and SQL comments."""
    statements: list[str] = []
    buffer: list[str] = []
    quote: str | None = None
    line_comment = False
    block_comment = False
    index = 0

    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""

        if line_comment:
            if char == "\n":
                line_comment = False
                buffer.append(char)
            index += 1
            continue

        if block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue

        if quote is None and char == "-" and next_char == "-":
            line_comment = True
            index += 2
            continue
        if quote is None and char == "/" and next_char == "*":
            block_comment = True
            index += 2
            continue

        if quote is not None:
            buffer.append(char)
            if char == quote:
                if next_char == quote and quote in {"'", '"', "`"}:
                    buffer.append(next_char)
                    index += 2
                    continue
                quote = None
            elif char == "\\" and next_char:
                buffer.append(next_char)
                index += 2
                continue
            index += 1
            continue

        if char in {"'", '"', "`"}:
            quote = char
            buffer.append(char)
            index += 1
            continue

        if char == ";":
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
            index += 1
            continue

        buffer.append(char)
        index += 1

    trailing = "".join(buffer).strip()
    if trailing:
        statements.append(trailing)
    return statements


def execute_sql_files(spark: object, files: list[Path]) -> list[dict[str, object]]:
    execution_log: list[dict[str, object]] = []
    for path in files:
        statements = split_sql(path.read_text(encoding="utf-8"))
        for statement_number, statement in enumerate(statements, start=1):
            spark.sql(statement)  # type: ignore[attr-defined]
            execution_log.append(
                {
                    "file": path.as_posix(),
                    "statement_number": statement_number,
                    "statement_sha256": hashlib.sha256(statement.encode("utf-8")).hexdigest(),
                }
            )
    return execution_log
