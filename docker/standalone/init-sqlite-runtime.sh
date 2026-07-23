#!/usr/bin/env bash
set -euo pipefail

SQLITE_PATH="${SQLITE_PATH:-/app/runtime_data/jiangxi.sqlite3}"
RUNTIME_DIR="$(dirname "${SQLITE_PATH}")"

mkdir -p "${RUNTIME_DIR}"
touch "${SQLITE_PATH}"

echo "[standalone] sqlite runtime prepared at ${SQLITE_PATH}"
