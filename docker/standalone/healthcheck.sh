#!/usr/bin/env bash
set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-5008}"
MINER_BACKEND_PORT="${MINER_BACKEND_PORT:-8000}"
MINER_FRONTEND_PORT="${MINER_FRONTEND_PORT:-4000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
MANIFEST_PATH="${JIANGXI_ASSET_MANIFEST_PATH:-/app/runtime_data/Jiangxi_asset_manifest.json}"

PYTHON_BIN="${JIANGXI_PYTHON_BIN:-python}"
if [ -x /opt/conda/envs/MMSeg310/bin/python ]; then
  PYTHON_BIN="/opt/conda/envs/MMSeg310/bin/python"
fi

is_gpu_inference_device() {
  case "${JIANGXI_INFERENCE_DEVICE:-cpu}" in
    cuda|cuda:0)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

http_get() {
  "${PYTHON_BIN}" - "$1" <<'PY'
import sys
from urllib.request import urlopen

# timeout=2：http_get 串行 4 次，最坏 4x5s=20s 会吃穿 HEALTHCHECK 预算
with urlopen(sys.argv[1], timeout=2) as response:
    if response.status < 200 or response.status >= 300:
        raise SystemExit(f"HTTP status {response.status}")
    sys.stdout.write(response.read().decode("utf-8"))
PY
}

# backend 根路径无路由（404 语义修复后不再被吞成 200）——探测会话端点：
# 未登录也返回 200 JSON，是 backend 存活的真实信号
http_get "http://127.0.0.1:${BACKEND_PORT}/api/auth/session" >/dev/null
http_get "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null
http_get "http://127.0.0.1:${MINER_FRONTEND_PORT}/" >/dev/null

health_json="$(http_get "http://127.0.0.1:${MINER_BACKEND_PORT}/api/health/jiangxi")"
"${PYTHON_BIN}" - "${health_json}" "${MANIFEST_PATH}" "${JIANGXI_EXPECTED_COUNT:-348}" "${JIANGXI_INFERENCE_DEVICE:-cpu}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

health = json.loads(sys.argv[1])
manifest_path = Path(sys.argv[2])
expected_count = int(sys.argv[3])
expected_device = sys.argv[4].strip().lower()
if expected_device == "cuda":
    expected_device = "cuda:0"
if health.get("status") != "ok":
    raise SystemExit("jiangxi health status is not ok")
if health.get("mine_count") != expected_count or health.get("unique_tbbh_count") != expected_count:
    raise SystemExit(f"jiangxi feature count mismatch: {health}")
if health.get("model_device") != expected_device:
    raise SystemExit(
        f"jiangxi inference device mismatch: {health.get('model_device')} != {expected_device}"
    )
if not manifest_path.is_file():
    raise SystemExit(f"manifest missing: {manifest_path}")
digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
if health.get("manifest_sha256") != digest:
    raise SystemExit("manifest hash reported by miner does not match the mounted file")
PY

if is_gpu_inference_device; then
  # ping 超时放宽到 10s：worker 串行设计下长推理期间 ping 需排队，2s 会误报不可用
  JIANGXI_MMSEG_WORKER_PING_TIMEOUT="${JIANGXI_MMSEG_WORKER_PING_TIMEOUT:-10}" \
    "${PYTHON_BIN}" /app/backend/applications/interface/mmseg_worker.py \
    --socket "${JIANGXI_MMSEG_WORKER_SOCKET:-/tmp/jiangxi-mmseg-worker.sock}" \
    --ping \
    --expect-device "${JIANGXI_INFERENCE_DEVICE:-cuda:0}" >/dev/null
else
  (cd /app/backend && "${PYTHON_BIN}" -c 'from applications.interface.mmseg_inference_caller import get_model_paths; get_model_paths("cc-ln/CUGRS"); print("jiangxi model assets passed")')
fi
