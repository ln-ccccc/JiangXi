# 江西单镜像运行目录

- `Dockerfile.jiangxi`: 江西专用单镜像构建入口
- `start-jiangxi-standalone.sh`: 单容器启动入口
- `init-sqlite-runtime.sh`: SQLite 运行时初始化
- `seed-jiangxi-runtime.sh`: 江西首次初始化导入
- `healthcheck.sh`: 单镜像健康检查
- `config.standalone.yaml`: 单镜像默认端口与运行配置

## SQLite 单镜像模式

- 数据库文件默认位于 `/app/runtime_data/jiangxi.sqlite3`
- `/app/runtime_data` 必须使用持久化卷；其中包含 SQLite、种子标记、资产 manifest 和
  `/app/runtime_data/change_matrix_outputs` 下的推理结果
- 首次启动会自动建库、建表、初始化管理员并导入江西数据
- 当前单镜像不再依赖 MySQL 服务端
- 运行时默认使用 `DB_BACKEND=sqlite`

## 运行数据准备

在执行构建前，请先将以下江西运行数据放入 `docker/standalone/runtime_data`：

- `Mine.csv`
- `348个图斑.shp`
- `348个图斑.shx`
- `348个图斑.dbf`
- `348个图斑.prj`
- `Jiangxi_NaturalMine.kmz`
- `Jiangxi_asset_manifest.json`

权威 Excel 位于 `miner/data/348图斑_TableMERNet无图像预测结果.xlsx`。构建前先运行：

```powershell
python backend/tools/validate_jiangxi_assets.py
python backend/tools/build_jiangxi_asset_manifest.py
```

manifest 记录文件哈希、记录数和完整的 `TBBH -> map_fid` 映射。运行时篡改或替换任一资产都会阻止启动。

启动时若种子标记仍在但 SQLite 业务表为空，脚本会在再次完成资产校验后自动重建江西默认项目；
若发现没有默认项目但仍有残留业务数据，则直接阻断启动，避免静默清空未知数据，需人工备份和恢复。

## 构建

```bash
docker build -f docker/standalone/Dockerfile.jiangxi -t geoview-jiangxi:standalone .
```

CPU 与 GPU 使用同一个构建入口，通过基础镜像和设备参数区分。推荐使用易记的稳定标签，同时保留带日期的不可变验收标签：

```powershell
docker build --progress=plain -f docker/standalone/Dockerfile.jiangxi `
  --build-arg JIANGXI_BASE_IMAGE=jiangxi-analysis-worker:gpu `
  --build-arg JIANGXI_RUNTIME_COMPAT_IMAGE=jiangxi-runtime:gpu `
  --build-arg JIANGXI_GPU_COMPAT_IMAGE=jiangxi-analysis-worker:gpu `
  --build-arg JIANGXI_INFERENCE_DEVICE=cuda:0 `
  -t geoview-jiangxi:jiangxi-gpu-YYYYMMDD `
  -t geoview-jiangxi:jiangxi-gpu .
```

默认使用本地 CPU 基础镜像 `jiangxi-runtime:current`；GPU 构建使用
`jiangxi-analysis-worker:gpu` 作为系统基础，并从 `jiangxi-runtime:gpu` 注入
`MMSeg310` Conda 环境和 Node 运行时，从 `jiangxi-analysis-worker:gpu` 复用同一 libc 下的
MMCV 原生扩展。构建不会自动拉取基础镜像，基础镜像标签不存在时应先导入正确的离线镜像归档。

不传 `JIANGXI_INFERENCE_DEVICE` 时为 CPU。GPU 构建必须传入 `cuda:0`，并使用带 CUDA 的本地基础镜像；构建阶段会验证 Torch 的 CUDA 构建和 MMSeg 依赖导入，运行阶段还会验证宿主机实际 GPU。GPU 容器必须以 `--gpus all` 启动。

镜像内的 Python 依赖必须来自预装的 `MMSeg310` 环境；主前端和 Miner 依赖均使用锁定的
`package-lock.json` 和本地 npm cache 执行 `npm ci --offline --include=dev`，构建过程禁止联网安装。

## 运行

如 `4173`、`4174` 或 `5178` 已被本机其他服务占用，请先确认冲突资源归属，再执行：

```bash
cp .env.example .env
# 编辑 .env，替换 ADMIN_PASSWORD 和 SECRET_KEY 占位符。
docker volume create jiangxi-runtime-data
docker run -d --name geoview-jiangxi --env-file .env \
  -v jiangxi-runtime-data:/app/runtime_data \
  -p 127.0.0.1:4173:4000 -p 127.0.0.1:4174:3000 -p 127.0.0.1:5178:5008 \
geoview-jiangxi:standalone
```

GPU 运行示例：

```powershell
docker run -d --name geoview-jiangxi-gpu --gpus all --env-file .env `
  -e DB_BACKEND=sqlite `
  -e SQLITE_PATH=/app/runtime_data/jiangxi.sqlite3 `
  -v jiangxi-runtime-gpu:/app/runtime_data `
  -p 127.0.0.1:4173:4000 -p 127.0.0.1:4174:3000 -p 127.0.0.1:5178:5008 `
  geoview-jiangxi:jiangxi-gpu
```

`ADMIN_PASSWORD` 和 `SECRET_KEY` 为必需环境变量。缺失时容器会在启动阶段失败并输出明确提示；不要在命令行或文档中写入真实凭据。
GPU standalone 与 CPU standalone 使用相同的公开地址：地图 `4173`、解译平台 `4174`、后端 `5178`。Standalone 始终使用挂载卷中的 SQLite，运行命令不得传入 MySQL 后端配置。
默认地图 provider 为 `gaode` 在线卫星底图；断网部署时请在环境文件中显式设置
`MINER_MAP_PROVIDER=offline`，或在具备本地 XYZ 瓦片时设置为 `local`。

## 验收

- 访问 Miner：`http://127.0.0.1:4173/#/map`
- 访问解译平台：`http://127.0.0.1:4174/#/segmentation`
- 访问后端：`http://127.0.0.1:5178`
- 登录后确认项目列表为江西默认项目
- 确认地图加载江西面图斑数据
- 确认主流程不再出现云南口径

健康检查会验证三个服务端口、348 条 GeoJSON 要素、TBBH 唯一性、manifest 哈希和模型资产。
GPU standalone 会在 Flask 前启动本地 Worker `/tmp/jiangxi-mmseg-worker.sock`：启动时只做一次模型
完整性校验与加载，后续请求串行复用该模型。GPU 健康检查只 ping 已就绪 Worker，不会每 30 秒重新
哈希权重；Worker 不可用时推理会明确失败，不会回退 CPU。CPU standalone 不启用该 Worker，仍保留
原有模型资产校验路径。
部署后可手动执行一次与容器设备一致的烟囱测试：

```bash
docker exec geoview-jiangxi-gpu python /app/backend/tools/jiangxi_cpu_smoke.py \
  --input-image /app/backend/test.tif
```

## 地物分类模型

运行地物分类前，必须在 `JIANGXI_MMSEG_MODEL_ROOT` 内提供江西专用的配置、权重、`metadata.json` 和受控源码目录，并通过对应环境变量指向文件。元数据必须声明 `region=jiangxi`、六类固定顺序以及配置、权重、源码树和依赖权重的 SHA-256。模型加载后还会校验实际类别和分类头数量。设备由 `JIANGXI_INFERENCE_DEVICE` 决定：默认 CPU，GPU 镜像显式使用 `cuda:0`；不会自动选择设备，也不会在 GPU 不可用时回退 CPU，更不会回退到云南模型。GPU Worker 运行状态可通过以下命令确认：

```bash
docker exec geoview-jiangxi-gpu /opt/conda/envs/MMSeg310/bin/python \
  /app/backend/applications/interface/mmseg_worker.py --ping \
  --socket /tmp/jiangxi-mmseg-worker.sock --expect-device cuda:0
```
