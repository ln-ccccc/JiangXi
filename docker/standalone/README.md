# 江西单镜像运行目录

- `Dockerfile.jiangxi`: 江西专用单镜像构建入口
- `start-jiangxi-standalone.sh`: 单容器启动入口
- `init-sqlite-runtime.sh`: SQLite 运行时初始化
- `seed-jiangxi-runtime.sh`: 江西首次初始化导入
- `healthcheck.sh`: 单镜像健康检查
- `config.standalone.yaml`: 单镜像默认端口与运行配置

## SQLite 单镜像模式

- 数据库文件默认位于 `/app/runtime_data/jiangxi.sqlite3`
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

## 构建

```bash
docker build -f docker/standalone/Dockerfile.jiangxi -t geoview-jiangxi:standalone .
```

## 运行

如 `4000` 或 `5008` 已被现有容器占用，请先停止占用端口的服务，再执行：

```bash
cp .env.example .env
# 编辑 .env，替换 ADMIN_PASSWORD 和 SECRET_KEY 占位符。
docker run -d --name geoview-jiangxi --env-file .env -p 4000:4000 -p 5008:5008 geoview-jiangxi:standalone
```

`ADMIN_PASSWORD` 和 `SECRET_KEY` 为必需环境变量。缺失时容器会在启动阶段失败并输出明确提示；不要在命令行或文档中写入真实凭据。

## 验收

- 访问 `http://127.0.0.1:4000`
- 访问 `http://127.0.0.1:5008`
- 登录后确认项目列表为江西默认项目
- 确认地图加载江西面图斑数据
- 确认主流程不再出现云南口径

## GPU 推理镜像（RTX 5060）

CPU 镜像 `Dockerfile.jiangxi` 保持不变。GPU 版使用 `Dockerfile.jiangxi.gpu`，首次构建会下载 CUDA 12.8 运行时并源码编译与 PyTorch 2.7 匹配的 MMCV；完成后可通过 `docker save` 离线交付。

```powershell
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
docker build -f docker/standalone/Dockerfile.jiangxi.gpu -t geoview-jiangxi:gpu .
.\docker\standalone\run-jiangxi-gpu.ps1
```

GPU 镜像以 `auto` 作为默认推理设备：容器获得 CUDA 时使用 `cuda:0`，否则明确显示降级原因并改用 CPU。显式选择 `cuda:0` 但未成功透传 GPU 时，接口会拒绝任务而不会伪装成 GPU 推理。KML ROI 在一个任务内只初始化一次模型，并拒绝并发任务以保护 8GB 显存。

Compose 部署使用 GPU 镜像并追加覆盖配置：

```powershell
$env:APP_IMAGE = 'geoview-jiangxi:gpu'
docker compose -f docker-compose.prod.yml -f docker-compose.gpu.yml up -d
```
