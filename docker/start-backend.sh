#!/usr/bin/env bash
set -euo pipefail

source /opt/conda/etc/profile.d/conda.sh
: "${GDAL_DATA:=}"
: "${GDAL_DRIVER_PATH:=}"
: "${GEOTIFF_CSV:=}"
: "${PROJ_LIB:=}"
: "${LIBXML2_DIR:=}"
conda activate MMSeg310

MMSEG_SOURCE="/app/backend/model/mmseg_config/dinov3_swinV1"
if [ -d "${MMSEG_SOURCE}/mmseg" ]; then
  export PYTHONPATH="${MMSEG_SOURCE}:${PYTHONPATH:-}"
fi

python /app/docker/wait-for-mysql.py
python /app/docker/write-runtime-env.py

cd /app/backend
exec python app.py
