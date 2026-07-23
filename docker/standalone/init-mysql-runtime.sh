#!/usr/bin/env bash
set -euo pipefail

MYSQL_DATA_DIR="${MYSQL_DATA_DIR:-/var/lib/jiangxi-standalone/mysql}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD is required}"
MYSQL_USERNAME="${MYSQL_USERNAME:-geoview}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:?MYSQL_PASSWORD is required}"
MYSQL_DATABASE="${MYSQL_DATABASE:-geoview}"
MYSQL_ROOT_HOST="${MYSQL_ROOT_HOST:-127.0.0.1}"
MYSQL_ROOT_PORT="${MYSQL_ROOT_PORT:-3306}"
MYSQL_SETUP_MARKER="${MYSQL_SETUP_MARKER:-/var/lib/jiangxi-standalone/.mysql-configured}"

require_sql_safe_value() {
  local name="$1"
  local value="$2"
  if [[ "${value}" == *"'"* || "${value}" == *"\\"* ]]; then
    echo "[standalone] ${name} cannot contain single quotes or backslashes" >&2
    exit 1
  fi
}

require_sql_safe_value "MYSQL_ROOT_PASSWORD" "${MYSQL_ROOT_PASSWORD}"
require_sql_safe_value "MYSQL_PASSWORD" "${MYSQL_PASSWORD}"
require_sql_safe_value "MYSQL_USERNAME" "${MYSQL_USERNAME}"

mkdir -p "${MYSQL_DATA_DIR}"

if [ ! -d "${MYSQL_DATA_DIR}/mysql" ]; then
  echo "[standalone] initializing mysql data dir at ${MYSQL_DATA_DIR}"
  mysqld \
    --defaults-file=/app/docker/standalone/mysql.cnf \
    --initialize-insecure \
    --user=root \
    --datadir="${MYSQL_DATA_DIR}"
fi

export MYSQL_HOST="${MYSQL_ROOT_HOST}"
export MYSQL_PORT="${MYSQL_ROOT_PORT}"

mysqld --defaults-file=/app/docker/standalone/mysql.cnf --user=root &
MYSQLD_PID=$!

python /app/docker/wait-for-mysql.py

MYSQL_ARGS=(--protocol=tcp "-h${MYSQL_ROOT_HOST}" "-P${MYSQL_ROOT_PORT}" -uroot)
if [ -f "${MYSQL_SETUP_MARKER}" ]; then
  MYSQL_ARGS+=("-p${MYSQL_ROOT_PASSWORD}")
fi

mysql "${MYSQL_ARGS[@]}" <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';
CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${MYSQL_USERNAME}'@'127.0.0.1' IDENTIFIED BY '${MYSQL_PASSWORD}';
CREATE USER IF NOT EXISTS '${MYSQL_USERNAME}'@'localhost' IDENTIFIED BY '${MYSQL_PASSWORD}';
ALTER USER '${MYSQL_USERNAME}'@'127.0.0.1' IDENTIFIED BY '${MYSQL_PASSWORD}';
ALTER USER '${MYSQL_USERNAME}'@'localhost' IDENTIFIED BY '${MYSQL_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_USERNAME}'@'127.0.0.1';
GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_USERNAME}'@'localhost';
FLUSH PRIVILEGES;
SQL

mkdir -p "$(dirname "${MYSQL_SETUP_MARKER}")"
touch "${MYSQL_SETUP_MARKER}"
echo "${MYSQLD_PID}" > /tmp/mysql-standalone.pid
echo "[standalone] mysql initialized and ready on ${MYSQL_ROOT_HOST}:${MYSQL_ROOT_PORT}"
