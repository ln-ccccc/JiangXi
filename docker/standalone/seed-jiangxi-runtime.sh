#!/usr/bin/env bash
set -euo pipefail

SEED_MARKER="${SEED_MARKER:-/app/runtime_data/.jiangxi-seeded}"
CSV_PATH="${CSV_PATH:-/app/runtime_data/Mine.csv}"
WORKBOOK_PATH="${MINER_ECOLOGY_WORKBOOK_PATH:-/app/miner/data/348图斑_TableMERNet无图像预测结果.xlsx}"
MINER_DEFAULT_GEO_SOURCE_PATH="${MINER_DEFAULT_GEO_SOURCE_PATH:-/app/runtime_data/348个图斑.shp}"
MINER_DEFAULT_KMZ_PATH="${MINER_DEFAULT_KMZ_PATH:-/app/runtime_data/Jiangxi_NaturalMine.kmz}"
MANIFEST_PATH="${JIANGXI_ASSET_MANIFEST_PATH:-/app/runtime_data/Jiangxi_asset_manifest.json}"
SEED_VERSION="${JIANGXI_SEED_VERSION:-2}"

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

if [ ! -f "${MANIFEST_PATH}" ]; then
  echo "[standalone] missing jiangxi asset manifest: ${MANIFEST_PATH}" >&2
  exit 1
fi

for sidecar in shx dbf prj; do
  if [ ! -f "${MINER_DEFAULT_GEO_SOURCE_PATH%.shp}.${sidecar}" ]; then
    echo "[standalone] missing SHP sidecar: ${MINER_DEFAULT_GEO_SOURCE_PATH%.shp}.${sidecar}" >&2
    exit 1
  fi
done

python /app/backend/tools/validate_jiangxi_assets.py \
  --excel "${WORKBOOK_PATH}" \
  --shp "${MINER_DEFAULT_GEO_SOURCE_PATH}" \
  --kmz "${MINER_DEFAULT_KMZ_PATH}" \
  --csv "${CSV_PATH}" \
  --expected-count "${JIANGXI_EXPECTED_COUNT:-348}" \
  --manifest "${MANIFEST_PATH}"

manifest_sha256="$(python - "${MANIFEST_PATH}" <<'PY'
import hashlib
import sys
from pathlib import Path

digest = hashlib.sha256()
with Path(sys.argv[1]).open('rb') as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(chunk)
print(digest.hexdigest())
PY
)"

if [ -f "${SEED_MARKER}" ]; then
  previous_sha256="$(python - "${SEED_MARKER}" <<'PY'
import json
import sys
from pathlib import Path

try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
except Exception:
    raise SystemExit(2)
print(data.get('asset_manifest_sha256', ''))
PY
  )" || {
    echo "[standalone] invalid seed marker; set JIANGXI_RESYNC=1 after review" >&2
    exit 1
  }
  if [ "${previous_sha256}" != "${manifest_sha256}" ] && [ "${JIANGXI_RESYNC:-0}" != "1" ]; then
    echo "[standalone] asset manifest changed; set JIANGXI_RESYNC=1 for an explicit resync" >&2
    exit 1
  fi
  if [ "${previous_sha256}" = "${manifest_sha256}" ]; then
    seed_state="$(
      cd /app/backend
      python - <<'PY'
import contextlib
import io

from applications import create_app
from applications.project_hub.jiangxi_seed_service import get_jiangxi_seed_database_state

with contextlib.redirect_stdout(io.StringIO()):
    app = create_app("production")
with app.app_context():
    print(get_jiangxi_seed_database_state())
PY
    )"
    case "${seed_state}" in
      ready)
        cd /app/backend
        python seed_jiangxi_from_csv.py \
          --csv-path "${CSV_PATH}" \
          --workbook-path "${WORKBOOK_PATH}" \
          --manifest "${MANIFEST_PATH}" \
          --sync-existing \
          --config "${FLASK_CONFIG}" \
          --actor standalone
        echo "[standalone] jiangxi project alignment checked"
        exit 0
        ;;
      empty)
        echo "[standalone] seed marker exists but database is empty; rebuilding jiangxi seed"
        ;;
      invalid)
        echo "[standalone] seed marker exists but database has no default jiangxi project and contains residual domain data; manual recovery required" >&2
        exit 1
        ;;
      *)
        echo "[standalone] unable to determine jiangxi seed database state: ${seed_state}" >&2
        exit 1
        ;;
    esac
  fi
fi

cd /app/backend
python seed_jiangxi_from_csv.py \
  --csv-path "${CSV_PATH}" \
  --workbook-path "${WORKBOOK_PATH}" \
  --manifest "${MANIFEST_PATH}" \
  --config "${FLASK_CONFIG}" \
  --actor standalone

mkdir -p "$(dirname "${SEED_MARKER}")"
python - "${SEED_MARKER}" "${manifest_sha256}" "${SEED_VERSION}" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(
    json.dumps(
        {
            'seed_version': sys.argv[3],
            'asset_manifest_sha256': sys.argv[2],
            'source': 'jiangxi_authoritative_assets',
        },
        ensure_ascii=False,
        indent=2,
    ) + '\n',
    encoding='utf-8',
)
PY
echo "[standalone] jiangxi seed completed"
