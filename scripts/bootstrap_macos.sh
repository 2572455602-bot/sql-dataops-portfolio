#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

JAVA_HOME_VALUE="${JAVA_HOME:-}"
if [[ -z "$JAVA_HOME_VALUE" && -x /usr/libexec/java_home ]]; then
  JAVA_HOME_VALUE="$(/usr/libexec/java_home -v 17 2>/dev/null || true)"
fi

JAVA_MAJOR=""
if [[ -n "$JAVA_HOME_VALUE" && -x "$JAVA_HOME_VALUE/bin/java" ]]; then
  JAVA_MAJOR="$("$JAVA_HOME_VALUE/bin/java" -version 2>&1 | head -n 1 | sed -E 's/.*version "([0-9]+).*/\1/')"
fi

if [[ "$JAVA_MAJOR" != "17" ]]; then
  JAVA_HOME_VALUE="$(python3 scripts/install_jdk.py | tail -n 1)"
fi

export JAVA_HOME="$JAVA_HOME_VALUE"
export PATH="$JAVA_HOME/bin:$PATH"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --disable-pip-version-check --upgrade pip
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
.venv/bin/python -m ecommerce_dataops.smoke

echo "Bootstrap complete: Java 17 and the Spark/Hive smoke test passed."
