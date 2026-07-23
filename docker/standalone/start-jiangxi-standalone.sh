#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/app"
CONFIG_PATH="${CONFIG_PATH:-/app/docker/standalone/config.standalone.yaml}"
RUNTIME_DATA_DIR="${RUNTIME_DATA_DIR:-/app/runtime_data}"
CSV_PATH="${CSV_PATH:-${RUNTIME_DATA_DIR}/Mine.csv}"
SQLITE_PATH="${SQLITE_PATH:-${RUNTIME_DATA_DIR}/jiangxi.sqlite3}"
MINER_DEFAULT_GEO_SOURCE_PATH="${MINER_DEFAULT_GEO_SOURCE_PATH:-${RUNTIME_DATA_DIR}/348个图斑.shp}"
MINER_DEFAULT_KMZ_PATH="${MINER_DEFAULT_KMZ_PATH:-${RUNTIME_DATA_DIR}/Jiangxi_NaturalMine.kmz}"

require_file() {
  local target="$1"
  if [ ! -f "$target" ]; then
    echo "[standalone] missing required file: $target" >&2
    exit 1
  fi
}

require_dir() {
  local target="$1"
  if [ ! -d "$target" ]; then
    echo "[standalone] missing required directory: $target" >&2
    exit 1
  fi
}

require_env() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "[standalone] missing required environment variable: $name" >&2
    exit 1
  fi
}

require_dir "${APP_ROOT}/backend"
require_dir "${APP_ROOT}/frontend"
require_dir "${APP_ROOT}/miner"
require_file "${APP_ROOT}/docker/standalone/init-sqlite-runtime.sh"
require_file "${APP_ROOT}/docker/standalone/seed-jiangxi-runtime.sh"
require_file "${APP_ROOT}/docker/standalone/healthcheck.sh"
require_file "${CONFIG_PATH}"
require_file "${CSV_PATH}"
require_file "${MINER_DEFAULT_GEO_SOURCE_PATH}"
if [ "${MINER_DEFAULT_GEO_SOURCE_PATH##*.}" = "shp" ]; then
  require_file "${MINER_DEFAULT_GEO_SOURCE_PATH%.shp}.shx"
  require_file "${MINER_DEFAULT_GEO_SOURCE_PATH%.shp}.dbf"
  require_file "${MINER_DEFAULT_GEO_SOURCE_PATH%.shp}.prj"
fi
require_env "ADMIN_PASSWORD"
require_env "SECRET_KEY"

echo "[standalone] preflight passed"

export STANDALONE_MODE=1
export DB_BACKEND="${DB_BACKEND:-sqlite}"
export CONFIG_PATH
export SQLITE_PATH
export CSV_PATH
export FLASK_CONFIG="${FLASK_CONFIG:-production}"
export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
export ADMIN_PASSWORD
export SECRET_KEY
export MINER_DEFAULT_GEO_SOURCE_PATH
export MINER_DEFAULT_KMZ_PATH
export MINER_MAP_PROVIDER="${MINER_MAP_PROVIDER:-gaode}"
export GEOVIEW_BACKEND_URL="${GEOVIEW_BACKEND_URL:-http://127.0.0.1:5008}"

bash "${APP_ROOT}/docker/standalone/init-sqlite-runtime.sh"
bash "${APP_ROOT}/docker/standalone/seed-jiangxi-runtime.sh"
echo "[standalone] jiangxi seed already completed or completed now"

exec bash "${APP_ROOT}/docker/entrypoint.sh"
