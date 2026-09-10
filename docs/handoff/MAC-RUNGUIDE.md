# 江西平台 · Mac 协作镜像 2026-09-10

## 包内容

| 文件 | 说明 |
| --- | --- |
| `jiangxi-cpu-20260910-ui.tar.gz` | CPU 镜像（含全部代码修复 + 新 UI + 32,214 张离线卫星瓦片 + 江西模型权重） |
| `jx_env_cpu_20260910.env` | 容器环境变量（含管理员账号；请勿外传） |
| `MAC-RUNGUIDE.md` | 本文档 |

## 镜像包含 / 不包含

**包含**：前后端全部代码（2026-09-10 main，commit `d874d2b`）、「山地制图台」新 UI、
工作台分页、离线瓦片裁剪修复、批量推理、348 图斑权威资产、江西专用模型。

**不包含**（部署时另行处理）：
- 甲方两期影像 189 个 tif（体积与授权原因未打包；如需推理测试请向项目负责人索取，
  `docker cp <目录>/. 容器名:/app/backend/bianhua_2years/`）
- 数据卷（首次启动自动创建，SQLite 数据落在容器卷内）

## Mac 部署步骤

前置：Docker Desktop（建议最新版，Apple Silicon 需开启 Rosetta 模拟：
Settings → General → Use Rosetta for x86_64/amd64 emulation）。

```bash
# 1. 导入镜像（约 10-20 分钟）
docker load -i jiangxi-cpu-20260910-ui.tar.gz

# 2. 启动（注意 --platform linux/amd64，无 --gpus）
docker run -d --name jiangxi-cpu \
  --platform linux/amd64 \
  --env-file jx_env_cpu_20260910.env \
  -p 127.0.0.1:4173:4000 -p 127.0.0.1:4174:3000 -p 127.0.0.1:5178:5008 \
  geoview-jiangxi:cpu-20260910-ui

# 3. 等待 healthy（首次约 2-4 分钟，Mac 模拟下更久）
docker inspect -f '{{.State.Health.Status}}' jiangxi-cpu

# 4. 打开
# 矿端地图     http://127.0.0.1:4173/#/map
# 解译平台     http://127.0.0.1:4174/#/segmentation
# 登录账号见 env 文件 ADMIN_USERNAME / ADMIN_PASSWORD
```

## 已知限制（Mac 模拟运行）

- 本镜像为 linux/amd64 架构，Apple Silicon 上经 Rosetta/QEMU 模拟运行——
  **界面交互正常，推理速度约为原生 Linux 的 1/5～1/10**；日常看界面、查数据、
  走流程足够，批量推理请在 GPU 机器执行。
- 停止/重启：`docker stop/start jiangxi-cpu`（数据保留在容器卷）。
- 日常协作以 git 分支 + PR 为准（github.com/ln-ccccc/JiangXi），镜像只是运行环境。

## 快速自检

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:4173/   # 应为 200
docker exec jiangxi-cpu sh -c 'find /app/miner/public/tiles -name "*.png" | wc -l'  # 应为 32214
```
