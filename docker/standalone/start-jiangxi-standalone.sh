#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/app"
CONFIG_PATH="${CONFIG_PATH:-/app/docker/standalone/config.standalone.yaml}"
RUNTIME_DATA_DIR="${RUNTIME_DATA_DIR:-/app/runtime_data}"
CSV_PATH="${CSV_PATH:-${RUNTIME_DATA_DIR}/Mine.csv}"
SQLITE_PATH="${SQLITE_PATH:-${RUNTIME_DATA_DIR}/jiangxi.sqlite3}"
MINER_DEFAULT_GEO_SOURCE_PATH="${MINER_DEFAULT_GEO_SOURCE_PATH:-${RUNTIME_DATA_DIR}/348个图斑.shp}"
MINER_DEFAULT_KMZ_PATH="${MINER_DEFAULT_KMZ_PATH:-${RUNTIME_DATA_DIR}/Jiangxi_NaturalMine.kmz}"
WORKBOOK_PATH="${MINER_ECOLOGY_WORKBOOK_PATH:-/app/miner/data/348图斑_TableMERNet无图像预测结果.xlsx}"
MANIFEST_PATH="${JIANGXI_ASSET_MANIFEST_PATH:-${RUNTIME_DATA_DIR}/Jiangxi_asset_manifest.json}"

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
require_file "${WORKBOOK_PATH}"
require_file "${MINER_DEFAULT_KMZ_PATH}"
require_file "${MANIFEST_PATH}"
require_file "${MINER_DEFAULT_GEO_SOURCE_PATH}"
if [ "${MINER_DEFAULT_GEO_SOURCE_PATH##*.}" = "shp" ]; then
  require_file "${MINER_DEFAULT_GEO_SOURCE_PATH%.shp}.shx"
  require_file "${MINER_DEFAULT_GEO_SOURCE_PATH%.shp}.dbf"
  require_file "${MINER_DEFAULT_GEO_SOURCE_PATH%.shp}.prj"
fi
require_env "ADMIN_PASSWORD"
require_env "SECRET_KEY"

echo "[standalone] preflight passed"

source /opt/conda/etc/profile.d/conda.sh
: "${GDAL_DATA:=}"
: "${GDAL_DRIVER_PATH:=}"
: "${GEOTIFF_CSV:=}"
: "${PROJ_LIB:=}"
: "${LIBXML2_DIR:=}"
conda activate MMSeg310

if [ -n "${JIANGXI_MMSEG_SOURCE_ROOT:-}" ] && [ -d "${JIANGXI_MMSEG_SOURCE_ROOT}/mmseg" ]; then
  export PYTHONPATH="${JIANGXI_MMSEG_SOURCE_ROOT}:${PYTHONPATH:-}"
fi

export STANDALONE_MODE=1
export DB_BACKEND="sqlite"
export CONFIG_PATH
export SQLITE_PATH
export CSV_PATH
export FLASK_CONFIG="${FLASK_CONFIG:-production}"
export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
export ADMIN_PASSWORD
export SECRET_KEY
export MINER_DEFAULT_GEO_SOURCE_PATH
export MINER_DEFAULT_KMZ_PATH
export MINER_ECOLOGY_WORKBOOK_PATH="${WORKBOOK_PATH}"
export JIANGXI_ASSET_MANIFEST_PATH="${MANIFEST_PATH}"
export JIANGXI_REQUIRE_ASSET_MANIFEST=1
export JIANGXI_EXPECTED_COUNT="${JIANGXI_EXPECTED_COUNT:-348}"
export JIANGXI_INFERENCE_DEVICE="${JIANGXI_INFERENCE_DEVICE:-cpu}"
export MINER_MAP_PROVIDER="${MINER_MAP_PROVIDER:-gaode}"
export MINER_CHANGE_OUTPUT_ROOT="${RUNTIME_DATA_DIR}/change_matrix_outputs"
export GEOVIEW_BACKEND_URL="${GEOVIEW_BACKEND_URL:-http://127.0.0.1:5008}"

if [ "${JIANGXI_INFERENCE_DEVICE}" = "cuda" ] || [ "${JIANGXI_INFERENCE_DEVICE}" = "cuda:0" ]; then
  export JIANGXI_MMSEG_WORKER_ENABLED="1"
  export JIANGXI_MMSEG_WORKER_SOCKET="${JIANGXI_MMSEG_WORKER_SOCKET:-/tmp/jiangxi-mmseg-worker.sock}"
else
  export JIANGXI_MMSEG_WORKER_ENABLED="0"
  unset JIANGXI_MMSEG_WORKER_SOCKET
fi

cd /app/backend
if [ "${JIANGXI_MMSEG_WORKER_ENABLED}" = "1" ]; then
  echo "[standalone] GPU Worker will validate and load Jiangxi model assets once"
else
  python -c 'from applications.interface.mmseg_inference_caller import get_model_paths; get_model_paths("cc-ln/CUGRS"); print("[standalone] Jiangxi model assets passed")'
fi

bash "${APP_ROOT}/docker/standalone/init-sqlite-runtime.sh"
bash "${APP_ROOT}/docker/standalone/seed-jiangxi-runtime.sh"
echo "[standalone] jiangxi seed already completed or completed now"

exec bash "${APP_ROOT}/docker/entrypoint.sh"
