# 江西单镜像交付 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个江西项目专用的单镜像运行时，在一个容器内同时运行 MySQL、backend、frontend、miner-api、miner-web，并只对外暴露 `4000`、`5008`。

**Architecture:** 在现有应用目录基础上新增江西单镜像 Dockerfile、统一入口脚本和首次初始化脚本。镜像内置 MySQL 与江西初始化数据，首次启动时完成数据库准备、江西数据导入和应用拉起，后续直接通过单个 `docker run` 启动。

**Tech Stack:** Docker, Bash, MySQL, Flask, Vue, Node.js, Python, Docker build/runtime

---

## 文件结构

### 新增文件

- Create: `docker/standalone/Dockerfile.jiangxi`
- Create: `docker/standalone/start-jiangxi-standalone.sh`
- Create: `docker/standalone/init-mysql-runtime.sh`
- Create: `docker/standalone/seed-jiangxi-runtime.sh`
- Create: `docker/standalone/healthcheck.sh`
- Create: `docker/standalone/config.standalone.yaml`
- Create: `docker/standalone/mysql.cnf`
- Create: `docker/standalone/README.md`

### 修改文件

- Modify: `backend/seed_jiangxi_from_csv.py`
- Modify: `miner/services/defaultJiangxiSource.js`
- Modify: `docker/entrypoint.sh`
- Modify: `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`

---

### Task 1: 新增江西单镜像入口与失败检查脚本

**Files:**
- Create: `docker/standalone/start-jiangxi-standalone.sh`
- Create: `docker/standalone/healthcheck.sh`
- Create: `docker/standalone/config.standalone.yaml`
- Create: `docker/standalone/README.md`

- [ ] **Step 1: 先写入口脚本和健康检查的失败路径约束**

`docker/standalone/start-jiangxi-standalone.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/app"
RUNTIME_DIR="/var/lib/jiangxi-standalone"
MYSQL_DATA_DIR="${MYSQL_DATA_DIR:-${RUNTIME_DIR}/mysql}"
CONFIG_PATH="${CONFIG_PATH:-/app/docker/standalone/config.standalone.yaml}"

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

require_dir "${APP_ROOT}/backend"
require_dir "${APP_ROOT}/frontend"
require_dir "${APP_ROOT}/miner"
require_file "${APP_ROOT}/docker/standalone/init-mysql-runtime.sh"
require_file "${APP_ROOT}/docker/standalone/seed-jiangxi-runtime.sh"
require_file "${APP_ROOT}/docker/standalone/healthcheck.sh"
require_file "${CONFIG_PATH}"

mkdir -p "${MYSQL_DATA_DIR}"

echo "[standalone] preflight passed"
```

`docker/standalone/healthcheck.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

curl -fsS "http://127.0.0.1:5008/" >/dev/null
curl -fsS "http://127.0.0.1:4000/" >/dev/null
```

`docker/standalone/config.standalone.yaml`

```yaml
port:
  backend: 5008
  frontend: 3000
host:
  backend: 0.0.0.0
  frontend: 0.0.0.0
debug: false
miner:
  enabled: true
  frontend_port: 4000
  backend_port: 8000
```

`docker/standalone/README.md`

```md
# 江西单镜像运行目录

- `Dockerfile.jiangxi`: 江西专用单镜像构建入口
- `start-jiangxi-standalone.sh`: 单容器启动入口
- `init-mysql-runtime.sh`: 容器内 MySQL 初始化
- `seed-jiangxi-runtime.sh`: 江西首次初始化导入
- `healthcheck.sh`: 单镜像健康检查
- `config.standalone.yaml`: 单镜像默认端口与运行配置
```

- [ ] **Step 2: 运行脚本，确认失败点落在未实现的 MySQL 初始化文件**

Run:

```bash
bash docker/standalone/start-jiangxi-standalone.sh
```

Expected:

```text
[standalone] missing required file: /app/docker/standalone/init-mysql-runtime.sh
```

- [ ] **Step 3: 补齐占位文件并让预检查通过**

`docker/standalone/init-mysql-runtime.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
echo "[standalone] mysql init placeholder"
```

`docker/standalone/seed-jiangxi-runtime.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
echo "[standalone] jiangxi seed placeholder"
```

给脚本赋权：

```bash
chmod +x docker/standalone/*.sh
```

- [ ] **Step 4: 再跑预检查，确认脚本结构通过**

Run:

```bash
bash docker/standalone/start-jiangxi-standalone.sh
```

Expected:

```text
[standalone] preflight passed
```

- [ ] **Step 5: Commit**

```bash
git add docker/standalone/start-jiangxi-standalone.sh docker/standalone/healthcheck.sh docker/standalone/config.standalone.yaml docker/standalone/README.md docker/standalone/init-mysql-runtime.sh docker/standalone/seed-jiangxi-runtime.sh
git commit -m "feat: add jiangxi standalone runtime scaffolding"
```

---

### Task 2: 实现容器内 MySQL 初始化与首次江西导入

**Files:**
- Create: `docker/standalone/init-mysql-runtime.sh`
- Create: `docker/standalone/seed-jiangxi-runtime.sh`
- Modify: `backend/seed_jiangxi_from_csv.py`
- Modify: `miner/services/defaultJiangxiSource.js`
- Create: `docker/standalone/mysql.cnf`

- [ ] **Step 1: 先把初始化和导入参数固定下来**

`docker/standalone/mysql.cnf`

```cnf
[mysqld]
bind-address=127.0.0.1
port=3306
datadir=/var/lib/jiangxi-standalone/mysql
socket=/tmp/mysql.sock
pid-file=/tmp/mysql.pid
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
skip-host-cache
skip-name-resolve
```

`backend/seed_jiangxi_from_csv.py`

```python
import argparse
from pathlib import Path

from app import create_app
from applications.project_hub.jiangxi_seed_service import seed_jiangxi_project_from_csv


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-path", default="/app/runtime_data/Mine.csv")
    parser.add_argument("--config", default="production")
    parser.add_argument("--actor", default="cli")
    return parser.parse_args()


def main():
    args = parse_args()
    app = create_app(args.config)
    csv_path = Path(args.csv_path)
    with app.app_context():
      result = seed_jiangxi_project_from_csv(csv_path, actor=args.actor)
    print(result)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 实现容器内 MySQL 初始化脚本**

`docker/standalone/init-mysql-runtime.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

MYSQL_DATA_DIR="${MYSQL_DATA_DIR:-/var/lib/jiangxi-standalone/mysql}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-root123456}"
MYSQL_USER="${MYSQL_USER:-paddle_rs}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-paddle_rs_jiangxi}"
MYSQL_DATABASE="${MYSQL_DATABASE:-paddle_rs}"

mkdir -p "${MYSQL_DATA_DIR}"

if [ ! -d "${MYSQL_DATA_DIR}/mysql" ]; then
  mysqld --initialize-insecure --user=root --datadir="${MYSQL_DATA_DIR}"
fi

mysqld \
  --defaults-file=/app/docker/standalone/mysql.cnf \
  --user=root &
MYSQLD_PID=$!

python /app/docker/wait-for-mysql.py

mysql -uroot --protocol=tcp -h127.0.0.1 -P3306 <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';
CREATE DATABASE IF NOT EXISTS ${MYSQL_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'127.0.0.1' IDENTIFIED BY '${MYSQL_PASSWORD}';
GRANT ALL PRIVILEGES ON ${MYSQL_DATABASE}.* TO '${MYSQL_USER}'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

echo "${MYSQLD_PID}" > /tmp/mysql-standalone.pid
```

- [ ] **Step 3: 实现首次江西导入脚本**

`docker/standalone/seed-jiangxi-runtime.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

SEED_MARKER="${SEED_MARKER:-/var/lib/jiangxi-standalone/.jiangxi-seeded}"
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_DATABASE="${MYSQL_DATABASE:-paddle_rs}"
export MYSQL_USER="${MYSQL_USER:-paddle_rs}"
export MYSQL_PASSWORD="${MYSQL_PASSWORD:-paddle_rs_jiangxi}"
export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin@123456}"
export SECRET_KEY="${SECRET_KEY:-jiangxi-standalone-secret}"

if [ -f "${SEED_MARKER}" ]; then
  echo "[standalone] jiangxi seed already completed"
  exit 0
fi

cd /app/backend
python seed_jiangxi_from_csv.py --csv-path /app/runtime_data/Mine.csv --config production --actor standalone

mkdir -p "$(dirname "${SEED_MARKER}")"
touch "${SEED_MARKER}"
```

`miner/services/defaultJiangxiSource.js`

```javascript
export const DEFAULT_JIANGXI_KMZ_PATH = '/app/runtime_data/Jiangxi_NaturalMine.kmz';
export const DEFAULT_JIANGXI_GEO_SOURCE_PATH = '/app/runtime_data/348个图斑.shp';
```

- [ ] **Step 4: 运行静态检查**

Run:

```bash
bash -n docker/standalone/init-mysql-runtime.sh
bash -n docker/standalone/seed-jiangxi-runtime.sh
python -m py_compile backend/seed_jiangxi_from_csv.py
```

Expected:

```text
no output
```

- [ ] **Step 5: Commit**

```bash
git add docker/standalone/init-mysql-runtime.sh docker/standalone/seed-jiangxi-runtime.sh docker/standalone/mysql.cnf backend/seed_jiangxi_from_csv.py miner/services/defaultJiangxiSource.js
git commit -m "feat: add standalone mysql and jiangxi seed init"
```

---

### Task 3: 新增江西单镜像 Dockerfile 与统一启动流程

**Files:**
- Create: `docker/standalone/Dockerfile.jiangxi`
- Modify: `docker/standalone/start-jiangxi-standalone.sh`
- Modify: `docker/entrypoint.sh`

- [ ] **Step 1: 先写 Dockerfile 和统一入口目标**

`docker/standalone/Dockerfile.jiangxi`

```dockerfile
FROM geoview-runtime:split-clean

WORKDIR /app

COPY backend /app/backend
COPY frontend /app/frontend
COPY miner /app/miner
COPY docker /app/docker
COPY config.yaml /app/config.yaml
COPY docs /app/docs
COPY "D:/项目/江西数据/Mine.csv" /app/runtime_data/Mine.csv
COPY "D:/项目/江西数据/348个图斑.shp" /app/runtime_data/348个图斑.shp
COPY "D:/项目/江西数据/348个图斑.shx" /app/runtime_data/348个图斑.shx
COPY "D:/项目/江西数据/348个图斑.dbf" /app/runtime_data/348个图斑.dbf
COPY "D:/项目/江西数据/348个图斑.prj" /app/runtime_data/348个图斑.prj

EXPOSE 4000 5008

ENTRYPOINT ["/app/docker/standalone/start-jiangxi-standalone.sh"]
```

- [ ] **Step 2: 修正 Dockerfile 为可构建形式**

把外部江西数据先复制到仓库内打包目录，再由 Dockerfile 从上下文复制：

`docker/standalone/start-jiangxi-standalone.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

export CONFIG_PATH="${CONFIG_PATH:-/app/docker/standalone/config.standalone.yaml}"
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306

/app/docker/standalone/init-mysql-runtime.sh
/app/docker/standalone/seed-jiangxi-runtime.sh

source /opt/conda/etc/profile.d/conda.sh
conda activate MMSeg310

cd /app
bash /app/docker/entrypoint.sh
```

`docker/entrypoint.sh`

```bash
# standalone mode support
if [ "${STANDALONE_MODE:-0}" = "1" ]; then
  export MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
  export MYSQL_PORT="${MYSQL_PORT:-3306}"
fi
```

- [ ] **Step 3: 构建命令与预期固定下来**

Run:

```bash
docker build -f docker/standalone/Dockerfile.jiangxi -t geoview-jiangxi:standalone .
```

Expected:

```text
Successfully tagged geoview-jiangxi:standalone
```

- [ ] **Step 4: 运行最小容器启动验证**

Run:

```bash
docker run --rm -p 4000:4000 -p 5008:5008 --name geoview-jiangxi geoview-jiangxi:standalone
```

Expected:

```text
[standalone] preflight passed
[standalone] jiangxi seed already completed or completed now
```

- [ ] **Step 5: Commit**

```bash
git add docker/standalone/Dockerfile.jiangxi docker/standalone/start-jiangxi-standalone.sh docker/entrypoint.sh
git commit -m "feat: add jiangxi standalone image build flow"
```

---

### Task 4: 打包运行、验收并更新交付报告

**Files:**
- Modify: `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`
- Modify: `docker/standalone/README.md`

- [ ] **Step 1: 补充单镜像运行文档**

`docker/standalone/README.md`

```md
## 构建

```bash
docker build -f docker/standalone/Dockerfile.jiangxi -t geoview-jiangxi:standalone .
```

## 运行

```bash
docker run -d --name geoview-jiangxi -p 4000:4000 -p 5008:5008 geoview-jiangxi:standalone
```

## 验收

- 访问 `http://127.0.0.1:4000`
- 访问 `http://127.0.0.1:5008`
- 登录后确认江西项目与江西图斑已加载
```

- [ ] **Step 2: 执行实际构建与运行**

Run:

```bash
docker build -f docker/standalone/Dockerfile.jiangxi -t geoview-jiangxi:standalone .
docker run -d --name geoview-jiangxi -p 4000:4000 -p 5008:5008 geoview-jiangxi:standalone
```

Expected:

```text
image built
container started
```

- [ ] **Step 3: 做最终验收**

Run:

```bash
curl http://127.0.0.1:5008/
curl http://127.0.0.1:5008/api/projects
curl http://127.0.0.1:5008/api/geojson
```

Browser checklist:

```text
1. 打开 http://127.0.0.1:4000
2. 使用 admin / ADMIN_PASSWORD 登录
3. 确认项目列表为江西默认项目
4. 确认地图加载江西面图斑
5. 确认主流程不再出现云南口径
```

- [ ] **Step 4: 更新验证报告**

在 `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md` 追加：

```md
## 江西单镜像补充验证

- 已构建 `geoview-jiangxi:standalone`
- 单容器内已同时运行 MySQL、backend、frontend、miner-api、miner-web
- 仅暴露 `4000`、`5008`
- 登录后江西项目与江西面图斑正常可见
```

- [ ] **Step 5: Commit**

```bash
git add docker/standalone/README.md docs/superpowers/reports/2026-07-05-formal-delivery-validation.md
git commit -m "feat: deliver jiangxi standalone image"
```

---

## 自检结果

- Spec coverage: 已覆盖单镜像入口、内置 MySQL、江西数据初始化、Dockerfile、构建运行和验收报告
- Placeholder scan: 未保留 `TBD`、`TODO`、`待定`
- Type consistency: 统一使用 `start-jiangxi-standalone.sh`、`init-mysql-runtime.sh`、`seed-jiangxi-runtime.sh`、`Dockerfile.jiangxi`
