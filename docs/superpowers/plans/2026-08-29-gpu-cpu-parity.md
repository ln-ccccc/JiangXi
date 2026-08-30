# GPU 与 CPU 使用体验一致性 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 GPU standalone 的默认入口、前端地址、SQLite 配置和持久化行为与 CPU standalone 一致。

**Architecture:** Standalone 启动脚本负责明确的 SQLite 环境和公开地址；`docker/write-runtime-env.py` 是前端运行时配置的唯一写入者；后端仅读取 runtime config，不在 standalone 模式覆盖该文件。GPU 继续使用同一个 TBBH/SQLite 数据卷和模型资产。

**Tech Stack:** Flask、Vue CLI、Vite、Docker Desktop、SQLite、PyTorch CUDA。

---

### Task 1: 防止 standalone 后端覆盖前端运行时配置

**Files:**

- Modify: `backend/app.py`
- Create: `backend/test_standalone_frontend_runtime_config.py`

- [ ] **Step 1: 写失败测试**

测试 standalone 启动路径不会写 `frontend/.env`，同时非 standalone 路径仍保留旧的开发环境兼容写入。

- [ ] **Step 2: 验证测试失败**

Run: `python -m unittest backend.test_standalone_frontend_runtime_config -v`

Expected: FAIL，因为当前 `backend/app.py` 无条件重写 `frontend/.env`。

- [ ] **Step 3: 最小实现**

将运行配置读取改为 `CONFIG_PATH` 优先；仅在 `STANDALONE_MODE != "1"` 时写旧版前端 `.env`。

- [ ] **Step 4: 验证测试通过**

Run: `python -m unittest backend.test_standalone_frontend_runtime_config -v`

Expected: PASS。

### Task 2: 固定 standalone SQLite 与 CPU 默认公开地址

**Files:**

- Modify: `docker/standalone/start-jiangxi-standalone.sh`
- Modify: `docker/entrypoint.sh`
- Modify: `docker/tests/test_source_isolation.py`

- [ ] **Step 1: 写失败测试**

断言 standalone 启动脚本无条件导出 `DB_BACKEND=sqlite`，并保留 CPU 既有公开地址 `4173/4174/5178`。

- [ ] **Step 2: 验证测试失败**

Run: `python -m unittest docker.tests.test_source_isolation.JiangxiSourceIsolationTests -v`

Expected: FAIL，因为 `entrypoint.sh` 目前可能继承外部 MySQL 配置。

- [ ] **Step 3: 最小实现**

在 standalone 入口固定导出 SQLite；在 entrypoint 的 standalone 分支再次覆盖为 SQLite，避免启动脚本和 `docker exec` 配置产生歧义。

- [ ] **Step 4: 验证测试通过**

Run: `python -m unittest docker.tests.test_source_isolation.JiangxiSourceIsolationTests -v`

Expected: PASS。

### Task 3: GPU 重建与保留数据的运行验证

**Files:**

- Modify: `docker/standalone/README.md`
- Modify: `docs/offline_deployment_guide.md`

- [ ] **Step 1: 更新运行命令**

文档明确 GPU 默认映射 `4173:4000`、`4174:3000`、`5178:5008`，并说明必须显式传入 `DB_BACKEND=sqlite`。

- [ ] **Step 2: 构建镜像**

在 Docker Desktop 的 F 盘数据目录下构建 `geoview-jiangxi:jiangxi-gpu`，不使用 C 盘存储。

- [ ] **Step 3: 重建容器并复用现有 volume**

停止当前 GPU 容器，保留并复用 `jiangxi-runtime-gpu-f-20260829c`；以 CPU 默认端口启动新的 GPU 容器。

- [ ] **Step 4: 验收**

验证主前端、地图、后端健康检查、管理员登录、348 条 GeoJSON、SQLite 进程环境、CUDA、TBBH manifest 和既有推理结果。
