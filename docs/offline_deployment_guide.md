# 江西独立工程部署指南

本文说明无外网环境下使用现有 Compose 部署江西工程。当前仓库不包含离线镜像归档；镜像归档必须由交付方另行提供并校验，不能从其他省份工程复用。

## 1. 部署目录与前提

在固定根目录执行：

```powershell
Set-Location 'D:\项目\JiangXi\JiangXi-Platform'
```

确认关键文件与江西种子数据存在：

```powershell
Test-Path docker-compose.prod.yml
Test-Path config.yaml
Test-Path .env.example
Test-Path 'docker/standalone/runtime_data/Jiangxi_NaturalMine.kmz'
Test-Path 'docker/standalone/runtime_data/Jiangxi_asset_manifest.json'
Test-Path 'docker/standalone/runtime_data/348个图斑.shp'
Test-Path 'docker/standalone/runtime_data/348个图斑.shx'
Test-Path 'docker/standalone/runtime_data/348个图斑.dbf'
Test-Path 'docker/standalone/runtime_data/348个图斑.prj'
Test-Path 'miner/data/348图斑_TableMERNet无图像预测结果.xlsx'
python backend/tools/validate_jiangxi_assets.py
```

默认运行镜像标签为 `jiangxi-runtime:current`。MySQL 镜像标签以 `.env.example` 的 `MYSQL_IMAGE` 为准。离线现场应在启动前分别加载交付方提供的镜像归档，并用 `docker image inspect` 确认标签存在；本文不假定归档文件名。

## 2. 创建部署环境文件

```powershell
Copy-Item .env.example .env
```

编辑未跟踪的 `.env`，至少替换以下占位符：

```text
ADMIN_PASSWORD=<管理员强密码>
SECRET_KEY=<随机应用密钥>
MYSQL_PASSWORD=<数据库用户强密码>
MYSQL_ROOT_PASSWORD=<数据库根用户强密码>
```

不要在文档、命令历史、聊天记录或版本库中写入真实值。保留以下江西配置：

```text
APP_IMAGE=jiangxi-runtime:current
SESSION_COOKIE_NAME=jiangxi_session
VITE_GEOVIEW_URL=http://127.0.0.1:4174/
VUE_APP_MINER_URL=http://127.0.0.1:4173/
VUE_APP_BACKEND_URL=http://127.0.0.1:5178/
MINER_MAP_PROVIDER=gaode
MINER_DEFAULT_KMZ_PATH=/app/runtime_data/Jiangxi_NaturalMine.kmz
MINER_DEFAULT_GEO_SOURCE_PATH=/app/runtime_data/348个图斑.shp
MINER_ECOLOGY_WORKBOOK_PATH=/app/miner/data/348图斑_TableMERNet无图像预测结果.xlsx
```

默认使用在线高德卫星底图。完全断网部署时，应显式设置 `MINER_MAP_PROVIDER=offline`；
如果已准备覆盖江西范围的本地 XYZ 瓦片，则设置为 `local` 并配置本地瓦片路径。

## 3. 校验并启动默认 CPU 栈

```powershell
docker compose --env-file .env -f docker-compose.prod.yml config
docker compose --env-file .env -f docker-compose.prod.yml up -d
docker compose --env-file .env -f docker-compose.prod.yml ps
```

解译方式默认为同步 CPU。GPU 不是自动选择，必须使用经过验证的 GPU 基础镜像、设置 `JIANGXI_INFERENCE_DEVICE=cuda:0` 并以 `--gpus all` 启动；CUDA 不可用时容器直接失败。

单镜像离线发布使用 `docker/standalone/Dockerfile.jiangxi`。必须给 `/app/runtime_data`
挂载命名卷，避免 SQLite、种子标记和 `/app/runtime_data/change_matrix_outputs` 下的
推理结果随容器重建丢失：

Dockerfile 默认使用本地 CPU 基础镜像 `jiangxi-runtime:current`，构建时不会联网拉取；若交付
包使用其他已核验的本地基础镜像，显式传入 `--build-arg JIANGXI_BASE_IMAGE=<本地标签>`，并在
构建前用 `docker image inspect` 确认该标签已导入。

推荐的 GPU 镜像标签为 `geoview-jiangxi:jiangxi-gpu`，同时使用带日期标签保存验收版本：

```powershell
docker build --progress=plain -f docker/standalone/Dockerfile.jiangxi `
  --build-arg JIANGXI_BASE_IMAGE=jiangxi-analysis-worker:gpu `
  --build-arg JIANGXI_RUNTIME_COMPAT_IMAGE=jiangxi-runtime:gpu `
  --build-arg JIANGXI_GPU_COMPAT_IMAGE=jiangxi-analysis-worker:gpu `
  --build-arg JIANGXI_INFERENCE_DEVICE=cuda:0 `
  -t geoview-jiangxi:jiangxi-gpu-YYYYMMDD `
  -t geoview-jiangxi:jiangxi-gpu .
```

```powershell
docker volume create jiangxi-runtime-data
docker run -d --name geoview-jiangxi --env-file .env `
  -e DB_BACKEND=sqlite `
  -e SQLITE_PATH=/app/runtime_data/jiangxi.sqlite3 `
  -v jiangxi-runtime-data:/app/runtime_data `
  -p 127.0.0.1:4173:4000 -p 127.0.0.1:4174:3000 -p 127.0.0.1:5178:5008 `
  geoview-jiangxi:standalone
```

GPU 单镜像使用相同的公开地址和 SQLite 配置，仅增加 GPU 设备参数：

```powershell
docker run -d --name geoview-jiangxi-gpu --gpus all --env-file .env `
  -e DB_BACKEND=sqlite `
  -e SQLITE_PATH=/app/runtime_data/jiangxi.sqlite3 `
  -e JIANGXI_INFERENCE_DEVICE=cuda:0 `
  -v jiangxi-runtime-gpu:/app/runtime_data `
  -p 127.0.0.1:4173:4000 -p 127.0.0.1:4174:3000 -p 127.0.0.1:5178:5008 `
  geoview-jiangxi:jiangxi-gpu
```

启动前会强制检查 Excel、SHP 全部 sidecar、KMZ、manifest 以及江西模型配置/权重/源码；
manifest 哈希变化时必须显式设置 `JIANGXI_RESYNC=1` 才允许重新同步。
若种子标记存在但 SQLite 业务表为空，启动脚本会在资产校验通过后重建默认项目；若存在残留业务数据
却缺少默认项目，则阻断启动并要求先人工备份、确认和恢复，避免自动清空未知数据。

## 4. 验证

```powershell
curl.exe -I 'http://127.0.0.1:4173/'
curl.exe -I 'http://127.0.0.1:4174/'
curl.exe -I 'http://127.0.0.1:5178/'
```

人工验收：

1. 打开 `http://127.0.0.1:4173/#/map` 并使用江西管理员账号登录。
2. 从 Miner 进入 `http://127.0.0.1:4174/#/segmentation`，确认不再次要求密码。
3. 确认页面身份为江西项目，执行方式显示同步 CPU。
4. 返回 Miner，确认会话保持。
5. 退出登录，确认两个江西前端同时失效。
6. 确认缺失入口配置时显示错误，不回退到其他项目。

GPU 验收还需确认容器健康状态中的 `model_device` 为 `cuda:0`，Torch 能看到宿主机显卡，
`mmcv.ops` 可导入，并完成一次限制数量的真实推理。GPU 验收通过前，不清理 CPU 回滚镜像。
GPU standalone 会在 Web 服务前启动本地常驻 MMSeg Worker，并在启动阶段完成一次完整模型校验和加载；
后续请求按单队列复用显存模型。其 Socket 仅在容器内的
`/tmp/jiangxi-mmseg-worker.sock` 监听，健康检查只执行 ping，不会周期性重新哈希大权重。若 Worker
未就绪、Socket 丢失或执行异常，GPU 推理必须明确失败，禁止回退到 CPU 或一次性模型进程。

检查单镜像健康状态：

```powershell
docker inspect --format '{{json .State.Health}}' geoview-jiangxi
docker exec geoview-jiangxi python /app/backend/tools/jiangxi_cpu_smoke.py `
  --input-image /app/backend/test.tif
```

Miner API 与 MySQL 仅在江西 Docker 网络内部，不能通过宿主机端口访问。Compose 展开结果中的宿主机端口必须全部绑定 `127.0.0.1`。

## 5. 江西地物分类模型

在 `.env` 中配置受控根目录 `JIANGXI_MMSEG_MODEL_ROOT` 以及配置、权重、元数据和源码路径。当前六类模型固定使用 `JIANGXI_MMSEG_SOURCE_ROOT=/app/backend/model/jiangxi/dinov3_swinV1`。所有路径必须位于受控根目录内。模型资产位于 `backend/model/jiangxi`，该目录不进入 Git，但必须随离线交付包提供；Docker 构建会把它打入江西镜像并删除父镜像残留的旧 `mmseg_config`，Compose 同时以只读挂载接入后端。

`metadata.json` 必须包含江西标识、固定六类顺序，以及配置、推理权重和定制 Python 源码树的 SHA-256：

```json
{
  "region": "jiangxi",
  "classes": ["grassland", "forest", "building", "road", "bareground", "water"],
  "config_sha256": "<config.py 的 64 位 SHA-256>",
  "checkpoint_sha256": "<model.pth 的 64 位 SHA-256>",
  "source_sha256": "<源码树内全部 .py 文件的确定性 64 位 SHA-256>",
  "source_file_count": 1211
}
```

后端会校验文件哈希和源码文件数；模型加载后还会核对实际 `dataset_meta.classes` 和分类头类别数。未配置、越界、哈希错误或实际类别不匹配时会明确失败，不使用云南模型。

归档训练 checkpoint 转换和审计使用：

```powershell
python backend/tools/migrate_jiangxi_checkpoint.py --source <训练checkpoint> --output backend/model/jiangxi/model.pth
python backend/tools/migrate_jiangxi_checkpoint.py --source <训练checkpoint> --output backend/model/jiangxi/model.pth --verify-only --expected-source-sha256 <源哈希> --expected-output-sha256 <目标哈希>
```

脚本会验证六类元数据，并逐项比较 `state_dict` 的键、形状、dtype 和张量值。

## 6. 数据初始化与迁移

江西数据库应从本仓库权威种子重建。默认不导入旧数据库、缓存或推理结果。人工确认的江西成果按 [legacy_data_migration.md](legacy_data_migration.md) 登记来源、目标和校验结果后再迁移。

天气/AQI 和在线底图在离线模式下显式关闭；缺失本地瓦片返回 404，不影响江西业务数据和推理主流程。

云南工程及其 Docker 网络、容器、镜像、卷、数据库和文件目录保持不变，部署命令不得引用或挂载。
