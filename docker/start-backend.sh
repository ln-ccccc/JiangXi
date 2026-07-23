#!/usr/bin/env bash
set -euo pipefail

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

python /app/docker/wait-for-mysql.py
python /app/docker/write-runtime-env.py

cd /app/backend
exec python app.py
