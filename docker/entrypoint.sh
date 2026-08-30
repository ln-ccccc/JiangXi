#!/usr/bin/env bash
set -euo pipefail

if [ "${STANDALONE_MODE:-0}" = "1" ]; then
  CONFIG_PATH="${CONFIG_PATH:-/app/docker/standalone/config.standalone.yaml}"
  export DB_BACKEND="sqlite"
  export SQLITE_PATH="${SQLITE_PATH:-/app/runtime_data/jiangxi.sqlite3}"
else
  CONFIG_PATH="${CONFIG_PATH:-/app/config.yaml}"
fi

DB_BACKEND_VALUE="$(printf '%s' "${DB_BACKEND:-mysql}" | tr '[:upper:]' '[:lower:]')"

source /opt/conda/etc/profile.d/conda.sh

# Predefine GDAL-specific variables to avoid set -u errors during activation
: "${GDAL_DATA:=}"
: "${GDAL_DRIVER_PATH:=}"
: "${GEOTIFF_CSV:=}"
: "${PROJ_LIB:=}"
: "${LIBXML2_DIR:=}"

conda activate MMSeg310

if [ -n "${JIANGXI_MMSEG_SOURCE_ROOT:-}" ] && [ -d "${JIANGXI_MMSEG_SOURCE_ROOT}/mmseg" ]; then
  export PYTHONPATH="${JIANGXI_MMSEG_SOURCE_ROOT}:${PYTHONPATH:-}"
fi

python - <<'PY'
import importlib.util
import os
import shutil
import sys

sys.path.insert(0, "/app/backend")

required = ("flask", "openpyxl", "rasterio", "torch", "mmseg", "mmcv", "mmdet")
missing = [name for name in required if importlib.util.find_spec(name) is None]
if importlib.util.find_spec("geopandas") is None and importlib.util.find_spec("osgeo") is None:
    missing.append("geopandas or osgeo")
if missing:
    raise SystemExit(
        "[entrypoint] Missing required offline runtime dependencies: " + ", ".join(missing)
    )
if shutil.which("node") is None:
    raise SystemExit("[entrypoint] Node.js is missing")
if not os.path.isdir("/app/miner/node_modules"):
    raise SystemExit("[entrypoint] Miner npm dependencies are missing: /app/miner/node_modules")
from applications.interface.inference_device import resolve_inference_device
runtime = resolve_inference_device(os.environ.get("JIANGXI_INFERENCE_DEVICE", "cpu"))
print(
    f"[entrypoint] inference device={runtime['effective_device']}"
    + (f" ({runtime['device_name']})" if runtime.get("device_name") else ""),
    flush=True,
)
print("[entrypoint] offline runtime dependencies passed", flush=True)
PY

CONFIG_EXPORTS=$(python - <<'PY'
import os
import yaml

config_path = os.environ.get("CONFIG_PATH", "/app/config.yaml")
with open(config_path, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

backend_host = cfg["host"]["backend"]
backend_port = cfg["port"]["backend"]
frontend_host = cfg["host"]["frontend"]
frontend_port = cfg["port"]["frontend"]

client_host = "localhost" if backend_host == "0.0.0.0" else backend_host

# Miner config
miner_cfg = cfg.get("miner", {})
miner_enabled = "true" if miner_cfg.get("enabled", False) else "false"
miner_frontend_port = miner_cfg.get("frontend_port", 4000)
miner_backend_port = miner_cfg.get("backend_port", 8000)

print(f"BACKEND_HOST={backend_host}")
print(f"BACKEND_PORT={backend_port}")
print(f"FRONTEND_HOST={frontend_host}")
print(f"FRONTEND_PORT={frontend_port}")
print(f"BACKEND_CLIENT_HOST={client_host}")
print(f"MINER_ENABLED={miner_enabled}")
print(f"MINER_FRONTEND_PORT={miner_frontend_port}")
print(f"MINER_BACKEND_PORT={miner_backend_port}")
PY
)

eval "${CONFIG_EXPORTS}"

export VUE_APP_MINER_URL="${VUE_APP_MINER_URL:-http://127.0.0.1:4173/}"
export VUE_APP_BACKEND_URL="${VUE_APP_BACKEND_URL:-http://127.0.0.1:5178/}"
export VITE_GEOVIEW_URL="${VITE_GEOVIEW_URL:-http://127.0.0.1:4174/}"
export MINER_MAP_PROVIDER="$(printf '%s' "${MINER_MAP_PROVIDER:-gaode}" | tr '[:upper:]' '[:lower:]')"
export MINER_LOCAL_TILE_URL="${MINER_LOCAL_TILE_URL:-/tiles/{z}/{x}/{y}.png}"
export MINER_LOCAL_TMS="${MINER_LOCAL_TMS:-0}"
python /app/docker/write-runtime-env.py

if [ "${DB_BACKEND_VALUE}" != "sqlite" ]; then
  python - <<'PY'
import os
import socket
import sys
import time

host = os.getenv("MYSQL_HOST", "127.0.0.1")
port = int(os.getenv("MYSQL_PORT", "3306"))

for attempt in range(30):
    try:
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        break
    except Exception as exc:
        wait = 2
        print(f"[entrypoint] Waiting for MySQL at {host}:{port} (attempt {attempt + 1}/30): {exc}", flush=True)
        time.sleep(wait)
else:
    print("[entrypoint] MySQL did not become available in time, exiting.", flush=True)
    sys.exit(1)
PY
fi

MMSEG_WORKER_PID=""

start_mmseg_worker() {
  if [ "${JIANGXI_MMSEG_WORKER_ENABLED:-0}" != "1" ]; then
    return
  fi

  local worker_socket="${JIANGXI_MMSEG_WORKER_SOCKET:-}"
  if [ -z "${worker_socket}" ]; then
    echo "[entrypoint] GPU Worker is enabled but no Socket path is configured" >&2
    exit 1
  fi

  echo "[entrypoint] Starting persistent MMSeg GPU Worker on ${worker_socket}"
  python /app/backend/applications/interface/mmseg_worker.py \
    --socket "${worker_socket}" \
    --device "${JIANGXI_INFERENCE_DEVICE:-cuda:0}" &
  MMSEG_WORKER_PID=$!

  local attempt
  for ((attempt = 1; attempt <= 120; attempt++)); do
    if python /app/backend/applications/interface/mmseg_worker.py \
      --socket "${worker_socket}" \
      --ping \
      --expect-device "${JIANGXI_INFERENCE_DEVICE:-cuda:0}" >/dev/null 2>&1; then
      echo "[entrypoint] MMSeg GPU Worker is ready (PID=${MMSEG_WORKER_PID})"
      return
    fi
    if ! kill -0 "${MMSEG_WORKER_PID}" 2>/dev/null; then
      wait "${MMSEG_WORKER_PID}" || true
      echo "[entrypoint] MMSeg GPU Worker exited before readiness" >&2
      exit 1
    fi
    sleep 1
  done

  echo "[entrypoint] MMSeg GPU Worker did not become ready in time" >&2
  kill -TERM "${MMSEG_WORKER_PID}" 2>/dev/null || true
  wait "${MMSEG_WORKER_PID}" 2>/dev/null || true
  exit 1
}

start_mmseg_worker

cd /app/backend
python app.py &
BACKEND_PID=$!

cd /app/frontend
npm run serve -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}" &
FRONTEND_PID=$!

# --- Miner (鐭垮北鐩戞祴绯荤粺) conditional startup ---
MINER_BACKEND_PID=""
MINER_FRONTEND_PID=""

if [ "${MINER_ENABLED}" = "true" ]; then
  echo "[entrypoint] Miner is ENABLED. Starting Miner services..."

  MINER_TDT_KEY="${MINER_TDT_KEY:-}"
  MINER_LOCAL_TILE_URL="${MINER_LOCAL_TILE_URL:-}"
  MINER_LOCAL_TMS="${MINER_LOCAL_TMS:-0}"
  export MINER_TDT_KEY MINER_LOCAL_TILE_URL MINER_LOCAL_TMS
  python /app/docker/write-runtime-env.py

  # Start Miner Express backend (using Node.js 20)
  cd /app/miner
  PATH=/opt/node20/bin:$PATH PORT=${MINER_BACKEND_PORT} GEOVIEW_BACKEND_URL="${GEOVIEW_BACKEND_URL:-http://localhost:${BACKEND_PORT}}" node server.js &
  MINER_BACKEND_PID=$!

  # Start Miner Vite dev server (using Node.js 20)
  cd /app/miner
  PATH=/opt/node20/bin:$PATH npx vite --host 0.0.0.0 --port "${MINER_FRONTEND_PORT}" &
  MINER_FRONTEND_PID=$!

  echo "[entrypoint] Miner backend PID=${MINER_BACKEND_PID}, frontend PID=${MINER_FRONTEND_PID}"
else
  echo "[entrypoint] Miner is DISABLED. Skipping Miner services."
fi

cd /app

WAIT_PIDS=("${BACKEND_PID}" "${FRONTEND_PID}")
if [ -n "${MMSEG_WORKER_PID}" ]; then
  WAIT_PIDS+=("${MMSEG_WORKER_PID}")
fi
if [ -n "${MINER_BACKEND_PID}" ]; then
  WAIT_PIDS+=("${MINER_BACKEND_PID}")
fi
if [ -n "${MINER_FRONTEND_PID}" ]; then
  WAIT_PIDS+=("${MINER_FRONTEND_PID}")
fi

terminate() {
  trap - SIGTERM SIGINT
  for pid in "${WAIT_PIDS[@]}"; do
    kill -TERM "${pid}" 2>/dev/null || true
  done
  wait "${WAIT_PIDS[@]}" 2>/dev/null || true
}

trap terminate SIGTERM SIGINT

wait -n "${WAIT_PIDS[@]}"
terminate
