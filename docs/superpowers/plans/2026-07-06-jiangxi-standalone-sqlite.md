# 江西单镜像 SQLite 交付 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前江西单镜像从依赖 MySQL 服务端的失败方案，收敛成一个基于 SQLite 单文件、保留完整业务主流程、只暴露 `4000/5008` 的可运行交付镜像。

**Architecture:** 保留现有单镜像目录和入口脚本，但移除容器内 `mysqld` 初始化链路，改为通过后端生产配置切换到 SQLite 单文件 `jiangxi.sqlite3`。镜像首次启动时自动创建库表、初始化管理员、导入江西项目数据，再启动 `backend/frontend/miner-api/miner-web` 四个应用进程。

**Tech Stack:** Docker, Bash, Python, Flask, SQLAlchemy, SQLite, Node.js, Vue, Docker build/runtime

---

## 文件结构

### 修改文件

- Modify: `backend/applications/configs/config.py`
- Modify: `backend/seed_jiangxi_from_csv.py`
- Modify: `docker/standalone/start-jiangxi-standalone.sh`
- Modify: `docker/standalone/seed-jiangxi-runtime.sh`
- Modify: `docker/standalone/Dockerfile.jiangxi`
- Modify: `docker/standalone/README.md`
- Modify: `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`

### 新增文件

- Create: `docker/standalone/init-sqlite-runtime.sh`

### 删除或停用文件

- Keep but stop using: `docker/standalone/init-mysql-runtime.sh`
- Keep but stop relying on env: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USERNAME`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`

---

### Task 1: 让生产配置支持 SQLite 并先用测试锁定行为

**Files:**
- Modify: `backend/applications/configs/config.py`
- Modify: `backend/seed_jiangxi_from_csv.py`
- Create or Modify: `backend/test_jiangxi_seed_service.py`

- [ ] **Step 1: 先补失败测试，锁定生产配置切到 SQLite 的行为**

在 `backend/test_jiangxi_seed_service.py` 追加：

```python
import os
import tempfile
import unittest
from pathlib import Path

from applications import create_app


class SQLiteProductionConfigTestCase(unittest.TestCase):
    def test_production_config_uses_sqlite_when_db_backend_is_sqlite(self):
        sqlite_path = Path(tempfile.mkdtemp(prefix="jiangxi_sqlite_")) / "jiangxi.sqlite3"
        old_backend = os.environ.get("DB_BACKEND")
        old_path = os.environ.get("SQLITE_PATH")
        old_secret = os.environ.get("SECRET_KEY")
        try:
            os.environ["DB_BACKEND"] = "sqlite"
            os.environ["SQLITE_PATH"] = str(sqlite_path)
            os.environ["SECRET_KEY"] = "sqlite-test-secret"
            app = create_app("production")
            uri = app.config["SQLALCHEMY_DATABASE_URI"]
            self.assertTrue(uri.startswith("sqlite:///"))
            self.assertIn("jiangxi.sqlite3", uri)
        finally:
            if old_backend is None:
                os.environ.pop("DB_BACKEND", None)
            else:
                os.environ["DB_BACKEND"] = old_backend
            if old_path is None:
                os.environ.pop("SQLITE_PATH", None)
            else:
                os.environ["SQLITE_PATH"] = old_path
            if old_secret is None:
                os.environ.pop("SECRET_KEY", None)
            else:
                os.environ["SECRET_KEY"] = old_secret
```

- [ ] **Step 2: 运行测试，确认当前先失败**

Run:

```bash
cd backend
.\.venv_task_20260705\Scripts\python.exe -m unittest test_jiangxi_seed_service.py -v
```

Expected:

```text
FAIL: test_production_config_uses_sqlite_when_db_backend_is_sqlite
AssertionError: False is not true
```

- [ ] **Step 3: 实现生产环境 SQLite 配置和导入脚本默认参数**

`backend/applications/configs/config.py`

```python
import logging
import os
from pathlib import Path
from urllib.parse import quote_plus


def _build_database_uri():
    backend = (os.getenv("DB_BACKEND") or "mysql").strip().lower()
    if backend == "sqlite":
        sqlite_path = Path(os.getenv("SQLITE_PATH") or "/app/runtime_data/jiangxi.sqlite3")
        return f"sqlite:///{sqlite_path.as_posix()}"

    mysql_username = os.getenv("MYSQL_USERNAME") or "root"
    mysql_password = os.getenv("MYSQL_PASSWORD") or "123456"
    mysql_host = os.getenv("MYSQL_HOST") or "127.0.0.1"
    mysql_port = int(os.getenv("MYSQL_PORT") or 3306)
    mysql_database = os.getenv("MYSQL_DATABASE") or "AdminFlask"
    return (
        "mysql+pymysql://"
        f"{mysql_username}:{quote_plus(mysql_password)}@{mysql_host}:{mysql_port}/{mysql_database}"
        "?charset=utf8mb4"
    )
```

```python
class BaseConfig:
    ...
    DB_BACKEND = (os.getenv("DB_BACKEND") or "mysql").strip().lower()
    SQLITE_PATH = os.getenv("SQLITE_PATH") or "/app/runtime_data/jiangxi.sqlite3"
    MYSQL_USERNAME = os.getenv("MYSQL_USERNAME") or "root"
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD") or "123456"
    MYSQL_HOST = os.getenv("MYSQL_HOST") or "127.0.0.1"
    MYSQL_PORT = int(os.getenv("MYSQL_PORT") or 3306)
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE") or "AdminFlask"
    SQLALCHEMY_DATABASE_URI = _build_database_uri()
```

`backend/seed_jiangxi_from_csv.py`

```python
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-path", default="/app/runtime_data/Mine.csv")
    parser.add_argument("--config", default=os.getenv("FLASK_CONFIG", "production"))
    parser.add_argument("--actor", default="cli")
    return parser.parse_args()
```

- [ ] **Step 4: 运行测试与语法检查**

Run:

```bash
cd backend
.\.venv_task_20260705\Scripts\python.exe -m unittest test_jiangxi_seed_service.py -v
.\.venv_task_20260705\Scripts\python.exe -m py_compile applications\configs\config.py seed_jiangxi_from_csv.py
```

Expected:

```text
OK
```

- [ ] **Step 5: Commit**

```bash
git add backend/applications/configs/config.py backend/seed_jiangxi_from_csv.py backend/test_jiangxi_seed_service.py
git commit -m "feat: support sqlite production config for jiangxi standalone"
```

---

### Task 2: 把 standalone 启动链路从 MySQL 改成 SQLite

**Files:**
- Create: `docker/standalone/init-sqlite-runtime.sh`
- Modify: `docker/standalone/start-jiangxi-standalone.sh`
- Modify: `docker/standalone/seed-jiangxi-runtime.sh`

- [ ] **Step 1: 先补 SQLite 初始化脚本和失败路径**

`docker/standalone/init-sqlite-runtime.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

SQLITE_PATH="${SQLITE_PATH:-/app/runtime_data/jiangxi.sqlite3}"
RUNTIME_DIR="$(dirname "${SQLITE_PATH}")"

mkdir -p "${RUNTIME_DIR}"
touch "${SQLITE_PATH}"

echo "[standalone] sqlite runtime prepared at ${SQLITE_PATH}"
```

把 `docker/standalone/start-jiangxi-standalone.sh` 中的 MySQL 依赖改成 SQLite 预检查：

```bash
require_file "${APP_ROOT}/docker/standalone/init-sqlite-runtime.sh"
...
SQLITE_PATH="${SQLITE_PATH:-${RUNTIME_DATA_DIR}/jiangxi.sqlite3}"
...
export DB_BACKEND="${DB_BACKEND:-sqlite}"
export SQLITE_PATH
```

- [ ] **Step 2: 运行脚本，确认当前仍会因为旧 MySQL 调用而失败**

Run:

```bash
bash docker/standalone/start-jiangxi-standalone.sh
```

Expected:

```text
/app/docker/standalone/init-mysql-runtime.sh: ... not found or mysqld related failure
```

- [ ] **Step 3: 完整替换启动与 seed 环境变量**

`docker/standalone/start-jiangxi-standalone.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/app"
RUNTIME_DATA_DIR="${RUNTIME_DATA_DIR:-/app/runtime_data}"
CONFIG_PATH="${CONFIG_PATH:-/app/docker/standalone/config.standalone.yaml}"
CSV_PATH="${CSV_PATH:-${RUNTIME_DATA_DIR}/Mine.csv}"
SQLITE_PATH="${SQLITE_PATH:-${RUNTIME_DATA_DIR}/jiangxi.sqlite3}"
MINER_DEFAULT_GEO_SOURCE_PATH="${MINER_DEFAULT_GEO_SOURCE_PATH:-${RUNTIME_DATA_DIR}/348个图斑.shp}"
MINER_DEFAULT_KMZ_PATH="${MINER_DEFAULT_KMZ_PATH:-${RUNTIME_DATA_DIR}/Jiangxi_NaturalMine.kmz}"

require_dir() { ... }
require_file() { ... }

require_dir "${APP_ROOT}/backend"
require_dir "${APP_ROOT}/frontend"
require_dir "${APP_ROOT}/miner"
require_file "${APP_ROOT}/docker/standalone/init-sqlite-runtime.sh"
require_file "${APP_ROOT}/docker/standalone/seed-jiangxi-runtime.sh"
require_file "${APP_ROOT}/docker/standalone/healthcheck.sh"
require_file "${CONFIG_PATH}"
require_file "${CSV_PATH}"
require_file "${MINER_DEFAULT_GEO_SOURCE_PATH}"
require_file "${MINER_DEFAULT_GEO_SOURCE_PATH%.shp}.shx"
require_file "${MINER_DEFAULT_GEO_SOURCE_PATH%.shp}.dbf"
require_file "${MINER_DEFAULT_GEO_SOURCE_PATH%.shp}.prj"

echo "[standalone] preflight passed"

export STANDALONE_MODE=1
export DB_BACKEND="${DB_BACKEND:-sqlite}"
export SQLITE_PATH
export CONFIG_PATH
export CSV_PATH
export MINER_DEFAULT_GEO_SOURCE_PATH
export MINER_DEFAULT_KMZ_PATH
export MINER_MAP_PROVIDER="${MINER_MAP_PROVIDER:-local}"
export GEOVIEW_BACKEND_URL="${GEOVIEW_BACKEND_URL:-http://127.0.0.1:5008}"

bash "${APP_ROOT}/docker/standalone/init-sqlite-runtime.sh"
bash "${APP_ROOT}/docker/standalone/seed-jiangxi-runtime.sh"
echo "[standalone] jiangxi seed already completed or completed now"

exec bash "${APP_ROOT}/docker/entrypoint.sh"
```

`docker/standalone/seed-jiangxi-runtime.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

SEED_MARKER="${SEED_MARKER:-/app/runtime_data/.jiangxi-seeded}"
export DB_BACKEND="${DB_BACKEND:-sqlite}"
export SQLITE_PATH="${SQLITE_PATH:-/app/runtime_data/jiangxi.sqlite3}"
export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin@123456}"
export SECRET_KEY="${SECRET_KEY:-jiangxi-standalone-secret}"

if [ -f "${SEED_MARKER}" ]; then
  echo "[standalone] jiangxi seed already completed"
  exit 0
fi

cd /app/backend
python seed_jiangxi_from_csv.py --csv-path /app/runtime_data/Mine.csv --config production --actor standalone

touch "${SEED_MARKER}"
```

- [ ] **Step 4: 运行静态检查**

Run:

```bash
bash -n docker/standalone/init-sqlite-runtime.sh
bash -n docker/standalone/start-jiangxi-standalone.sh
bash -n docker/standalone/seed-jiangxi-runtime.sh
```

Expected:

```text
no output
```

- [ ] **Step 5: Commit**

```bash
git add docker/standalone/init-sqlite-runtime.sh docker/standalone/start-jiangxi-standalone.sh docker/standalone/seed-jiangxi-runtime.sh
git commit -m "feat: switch jiangxi standalone startup to sqlite"
```

---

### Task 3: 调整 Dockerfile 和 entrypoint，去掉 MySQL 假设

**Files:**
- Modify: `docker/standalone/Dockerfile.jiangxi`
- Modify: `docker/entrypoint.sh`
- Modify: `docker/standalone/README.md`

- [ ] **Step 1: 先让 Dockerfile 默认使用 SQLite 模式**

`docker/standalone/Dockerfile.jiangxi`

```dockerfile
FROM geoview-runtime:split-clean

WORKDIR /app

ENV STANDALONE_MODE=1 \
    DB_BACKEND=sqlite \
    SQLITE_PATH=/app/runtime_data/jiangxi.sqlite3 \
    CONFIG_PATH=/app/docker/standalone/config.standalone.yaml \
    CSV_PATH=/app/runtime_data/Mine.csv \
    MINER_DEFAULT_GEO_SOURCE_PATH=/app/runtime_data/348个图斑.shp \
    MINER_DEFAULT_KMZ_PATH=/app/runtime_data/Jiangxi_NaturalMine.kmz \
    GEOVIEW_BACKEND_URL=http://127.0.0.1:5008 \
    MINER_MAP_PROVIDER=local

COPY backend /app/backend
COPY frontend /app/frontend
COPY miner /app/miner
COPY docker /app/docker
COPY config.yaml /app/config.yaml
COPY docker/standalone/runtime_data /app/runtime_data

RUN chmod +x /app/docker/entrypoint.sh /app/docker/*.sh /app/docker/standalone/*.sh

EXPOSE 4000 5008

HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD ["/app/docker/standalone/healthcheck.sh"]

ENTRYPOINT ["/app/docker/standalone/start-jiangxi-standalone.sh"]
```

- [ ] **Step 2: 修正 `docker/entrypoint.sh` 的 standalone 分支**

把 standalone 模式里的 MySQL 等待去掉，改成只在非 SQLite 模式等待：

```bash
DB_BACKEND_VALUE="$(printf '%s' "${DB_BACKEND:-mysql}" | tr '[:upper:]' '[:lower:]')"

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
        print(f"[entrypoint] Waiting for MySQL at {host}:{port} (attempt {attempt + 1}/30): {exc}", flush=True)
        time.sleep(2)
else:
    print("[entrypoint] MySQL did not become available in time, exiting.", flush=True)
    sys.exit(1)
PY
fi
```

- [ ] **Step 3: 更新 README 运行说明**

`docker/standalone/README.md`

```md
## SQLite 单镜像模式

- 数据库文件默认位于 `/app/runtime_data/jiangxi.sqlite3`
- 首次启动会自动建库、建表、初始化管理员并导入江西数据
- 不再依赖 MySQL 服务端

## 构建

```bash
docker build -f docker/standalone/Dockerfile.jiangxi -t geoview-jiangxi:standalone .
```

## 运行

```bash
docker run -d --name geoview-jiangxi -p 4000:4000 -p 5008:5008 geoview-jiangxi:standalone
```
```

- [ ] **Step 4: 做脚本和构建前检查**

Run:

```bash
bash -n docker/entrypoint.sh
bash -n docker/standalone/start-jiangxi-standalone.sh
```

Expected:

```text
no output
```

- [ ] **Step 5: Commit**

```bash
git add docker/standalone/Dockerfile.jiangxi docker/entrypoint.sh docker/standalone/README.md
git commit -m "feat: package jiangxi standalone image with sqlite"
```

---

### Task 4: 构建 SQLite 单镜像、运行验收并更新报告

**Files:**
- Modify: `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`

- [ ] **Step 1: 先写最终验收块**

在 `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md` 追加：

```md
## 江西单镜像 SQLite 补充验证

- 已切换为 SQLite 单文件运行
- 单镜像不再依赖 MySQL 服务端
- 首次启动会自动完成江西数据初始化
- `/api/projects` 返回江西默认项目
- `/api/geojson` 返回江西面图斑
```

- [ ] **Step 2: 构建镜像**

Run:

```bash
docker build --progress=plain -f docker/standalone/Dockerfile.jiangxi -t geoview-jiangxi:standalone .
```

Expected:

```text
Successfully tagged geoview-jiangxi:standalone
```

- [ ] **Step 3: 运行容器并做接口验收**

Run:

```bash
docker rm -f geoview-jiangxi 2>/dev/null || true
docker run -d --name geoview-jiangxi -p 4000:4000 -p 5008:5008 geoview-jiangxi:standalone
curl http://127.0.0.1:5008/
curl http://127.0.0.1:5008/api/projects
curl http://127.0.0.1:5008/api/geojson
```

Expected:

```text
backend reachable
/api/projects returns jiangxi default project
/api/geojson returns non-empty FeatureCollection
```

- [ ] **Step 4: 做浏览器验收**

Browser checklist:

```text
1. 打开 http://127.0.0.1:4000
2. 使用 admin / ADMIN_PASSWORD 登录
3. 确认项目列表为江西默认项目
4. 确认地图加载江西面图斑
5. 确认主流程不再出现云南口径
```

- [ ] **Step 5: 更新报告**

把以下结论写入 `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`：

```md
- 江西单镜像已改为 SQLite 单文件运行
- 容器无需 `mysqld`
- 登录、项目列表、江西图斑和工作台通过验收
```

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/reports/2026-07-05-formal-delivery-validation.md
git commit -m "feat: deliver jiangxi standalone sqlite image"
```

---

## 自检结果

- Spec coverage: 已覆盖生产配置 SQLite 化、standalone 启动链路切换、Dockerfile/entrypoint 调整、镜像构建运行和最终验收
- Placeholder scan: 未保留 `TBD`、`TODO`、`待定`
- Type consistency: 统一使用 `DB_BACKEND=sqlite`、`SQLITE_PATH=/app/runtime_data/jiangxi.sqlite3`、`init-sqlite-runtime.sh`
