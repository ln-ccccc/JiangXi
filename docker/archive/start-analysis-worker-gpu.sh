#!/usr/bin/env bash
# [归档 2026-09-15] 随 Dockerfile.jiangxi-analysis-worker-gpu 一并回收：该 Dockerfile
# COPY 本脚本至 /app/docker/ 并作为 GPU worker ENTRYPOINT。来源：
# .worktrees/jiangxi-platform-repair（fix/jiangxi-platform-repair，commit 698134e）。
# 现行 docker/standalone/Dockerfile.jiangxi 的 RUN rm 清单会把本脚本从 standalone
# 运行镜像剔除（复审 E 批镜像清理）；本归档仅服务 GPU worker 镜像的可追溯与重建。
set -euo pipefail

: "${JIANGXI_MMSEG_SOURCE_ROOT:=/app/backend/model/jiangxi/dinov3_swinV1}"
if [ -d "${JIANGXI_MMSEG_SOURCE_ROOT}/mmseg" ]; then
  export PYTHONPATH="${JIANGXI_MMSEG_SOURCE_ROOT}:${PYTHONPATH:-}"
fi

python /app/docker/wait-for-mysql.py
cd /app/backend
exec python analysis_worker.py
