#!/usr/bin/env bash
set -euo pipefail

SEED_MARKER="${SEED_MARKER:-/app/runtime_data/.jiangxi-seeded}"
CSV_PATH="${CSV_PATH:-/app/runtime_data/Mine.csv}"
WORKBOOK_PATH="${MINER_ECOLOGY_WORKBOOK_PATH:-/app/miner/data/348图斑_TableMERNet无图像预测结果.xlsx}"

export DB_BACKEND="${DB_BACKEND:-sqlite}"
export SQLITE_PATH="${SQLITE_PATH:-/app/runtime_data/jiangxi.sqlite3}"
export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
: "${ADMIN_PASSWORD:?ADMIN_PASSWORD is required}"
export ADMIN_PASSWORD
: "${SECRET_KEY:?SECRET_KEY is required}"
export SECRET_KEY
export FLASK_CONFIG="${FLASK_CONFIG:-production}"

if [ ! -f "${CSV_PATH}" ]; then
  echo "[standalone] missing jiangxi seed source: ${CSV_PATH}" >&2
  exit 1
fi

if [ ! -f "${WORKBOOK_PATH}" ]; then
  echo "[standalone] missing jiangxi workbook: ${WORKBOOK_PATH}" >&2
  exit 1
fi

cd /app/backend
if [ -f "${SEED_MARKER}" ]; then
  python seed_jiangxi_from_csv.py \
    --csv-path "${CSV_PATH}" \
    --workbook-path "${WORKBOOK_PATH}" \
    --sync-existing \
    --config "${FLASK_CONFIG}" \
    --actor standalone
  echo "[standalone] jiangxi project alignment checked"
  exit 0
fi

python seed_jiangxi_from_csv.py \
  --csv-path "${CSV_PATH}" \
  --workbook-path "${WORKBOOK_PATH}" \
  --config "${FLASK_CONFIG}" \
  --actor standalone

mkdir -p "$(dirname "${SEED_MARKER}")"
touch "${SEED_MARKER}"
echo "[standalone] jiangxi seed completed"
