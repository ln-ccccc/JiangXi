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
Test-Path 'docker/standalone/runtime_data/348个图斑.shp'
Test-Path 'docker/standalone/runtime_data/348个图斑.shx'
Test-Path 'docker/standalone/runtime_data/348个图斑.dbf'
Test-Path 'docker/standalone/runtime_data/348个图斑.prj'
Test-Path 'miner/data/348图斑_TableMERNet无图像预测结果.xlsx'
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
MINER_DEFAULT_KMZ_PATH=/app/runtime_data/Jiangxi_NaturalMine.kmz
MINER_DEFAULT_GEO_SOURCE_PATH=/app/runtime_data/348个图斑.shp
MINER_ECOLOGY_WORKBOOK_PATH=/app/miner/data/348图斑_TableMERNet无图像预测结果.xlsx
```

## 3. 校验并启动默认 CPU 栈

```powershell
docker compose --env-file .env -f docker-compose.prod.yml config
docker compose --env-file .env -f docker-compose.prod.yml up -d
docker compose --env-file .env -f docker-compose.prod.yml ps
```

解译方式固定为同步 CPU；江西工程不提供 GPU 覆盖文件。

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

云南工程及其 Docker 网络、容器、镜像、卷、数据库和文件目录保持不变，部署命令不得引用或挂载。
