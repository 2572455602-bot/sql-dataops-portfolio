#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "Missing .venv. Run: make bootstrap" >&2
  exit 2
fi

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ecommerce-dataops-recording.XXXXXX")"
RUNTIME_ROOT="$WORK_DIR/runtime"
SUCCESS_STDOUT="$WORK_DIR/success.out"
SUCCESS_STDERR="$WORK_DIR/success.err"
FAIL_STDOUT="$WORK_DIR/failure.out"
FAIL_STDERR="$WORK_DIR/failure.err"
BAD_DATA_DIR="$WORK_DIR/invalid-feature-dataset"
trap 'rm -rf "$WORK_DIR"' EXIT

publication_hash() {
  "$PYTHON" - "$1" <<'PY'
import hashlib
from pathlib import Path
import sys

directory = Path(sys.argv[1])
digest = hashlib.sha256()
for path in sorted(item for item in directory.iterdir() if item.is_file()):
    digest.update(path.name.encode("utf-8"))
    digest.update(path.read_bytes())
print(digest.hexdigest())
PY
}

PROJECT_PUBLICATION_HASH_BEFORE="absent"
if [[ -d "$ROOT/bi_exports/current" ]]; then
  PROJECT_PUBLICATION_HASH_BEFORE="$(publication_hash "$ROOT/bi_exports/current")"
fi
PROJECT_DEMO_HASH_BEFORE="absent"
if [[ -d "$ROOT/data/demo/ecommerce" ]]; then
  PROJECT_DEMO_HASH_BEFORE="$(publication_hash "$ROOT/data/demo/ecommerce")"
fi

echo "[1/4] Build a deterministic 40-user SparkSQL release in an isolated runtime"
if ! "$PYTHON" -m ecommerce_dataops.cli demo --users 40 --runtime-root "$RUNTIME_ROOT" \
  >"$SUCCESS_STDOUT" 2>"$SUCCESS_STDERR"; then
  tail -n 20 "$SUCCESS_STDERR" >&2
  exit 1
fi

echo "[2/4] Read the published manifest and quality evidence"
"$PYTHON" - "$RUNTIME_ROOT/bi_exports/current/manifest.json" <<'PY'
import json
from pathlib import Path
import sys

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
profile = manifest["data_profile"]
quality = manifest["quality"]
assert manifest["status"] == "success", manifest
assert manifest["published"] is True, manifest
assert quality["status"] == "pass", quality
assert quality["total_checks"] == 19, quality
assert quality["passed_checks"] == 18, quality
assert quality["failed_checks"] == 0, quality
assert quality["warning_checks"] == 1, quality
print(f"run_id={manifest['run_id']}")
print(f"mode={manifest['data_mode']} status={manifest['status']} published={manifest['published']}")
print(f"rows raw/valid/quarantine/dwd={profile['raw_rows']}/{profile['valid_rows']}/{profile['quarantine_rows']}/{profile['dwd_rows']}")
print(f"quality passed/total={quality['passed_checks']}/{quality['total_checks']}")
print("current_pointer=isolated_runtime/bi_exports/current")
PY

BEFORE_HASH="$(publication_hash "$RUNTIME_ROOT/bi_exports/current")"
"$PYTHON" - "$RUNTIME_ROOT/data/demo/ecommerce" "$BAD_DATA_DIR" <<'PY'
import csv
from decimal import Decimal
from pathlib import Path
import shutil
import sys

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
shutil.copytree(source, destination)

feature_path = destination / "user_features.csv"
with feature_path.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle)
    fieldnames = reader.fieldnames
    rows = list(reader)
assert fieldnames and rows
rows[0]["total_spent"] = str(Decimal(rows[0]["total_spent"]) + Decimal("1.00"))
with feature_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
PY

echo "[3/4] Run a bad batch; the blocking gate must return non-zero"
set +e
"$PYTHON" -m ecommerce_dataops.cli full --data-dir "$BAD_DATA_DIR" --runtime-root "$RUNTIME_ROOT" \
  >"$FAIL_STDOUT" 2>"$FAIL_STDERR"
FAIL_STATUS=$?
set -e
if [[ "$FAIL_STATUS" -eq 0 ]]; then
  echo "ERROR: the invalid batch unexpectedly succeeded" >&2
  exit 1
fi
tail -n 1 "$FAIL_STDERR"

"$PYTHON" - "$RUNTIME_ROOT" <<'PY'
import json
from pathlib import Path
import sys

runtime = Path(sys.argv[1])
manifests = sorted((runtime / "artifacts" / "runs").glob("*-portfolio-*/manifest.json"))
assert len(manifests) == 1, f"expected one PORTFOLIO failure manifest, found {len(manifests)}"
manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
quality = manifest.get("quality", {})
blocking = quality.get("blocking_checks", [])
assert manifest.get("status") == "failed", manifest
assert manifest.get("published") is False, manifest
assert manifest.get("error_type") == "QualityGateError", manifest
assert "user_feature_snapshot_reconciles" in blocking, blocking
print("rejection_reason=QualityGateError:user_feature_snapshot_reconciles")
print("rejection_reason_verified=yes")
PY

AFTER_HASH="$(publication_hash "$RUNTIME_ROOT/bi_exports/current")"
if [[ "$BEFORE_HASH" != "$AFTER_HASH" ]]; then
  echo "ERROR: the failed batch changed the last successful publication" >&2
  exit 1
fi

PROJECT_PUBLICATION_HASH_AFTER="absent"
if [[ -d "$ROOT/bi_exports/current" ]]; then
  PROJECT_PUBLICATION_HASH_AFTER="$(publication_hash "$ROOT/bi_exports/current")"
fi
PROJECT_DEMO_HASH_AFTER="absent"
if [[ -d "$ROOT/data/demo/ecommerce" ]]; then
  PROJECT_DEMO_HASH_AFTER="$(publication_hash "$ROOT/data/demo/ecommerce")"
fi
if [[ "$PROJECT_PUBLICATION_HASH_BEFORE" != "$PROJECT_PUBLICATION_HASH_AFTER" ]]; then
  echo "ERROR: isolated recording changed the project Dashboard publication" >&2
  exit 1
fi
if [[ "$PROJECT_DEMO_HASH_BEFORE" != "$PROJECT_DEMO_HASH_AFTER" ]]; then
  echo "ERROR: isolated recording changed the project DEMO fixture" >&2
  exit 1
fi

echo "[4/4] Prove failure safety"
echo "failed_exit_code=$FAIL_STATUS"
echo "rejection_reason_verified=yes"
echo "last_good_checksum_unchanged=yes"
echo "project_dashboard_unchanged=yes"
echo "project_demo_fixture_unchanged=yes"
echo "Recording demo complete. Explain: build -> validate -> publish -> reject bad batch -> preserve last good."
