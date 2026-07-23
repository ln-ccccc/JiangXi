# 江西独立工程系统说明

## 1. 系统组成与公开入口

| 组件 | 容器 | 宿主机访问 |
| --- | --- | --- |
| Miner 地图端 | `jiangxi-miner-web` | `http://127.0.0.1:4173/#/map` |
| 江西解译前端 | `jiangxi-frontend` | `http://127.0.0.1:4174/#/segmentation` |
| 业务后端 | `jiangxi-backend` | `http://127.0.0.1:5178` |
| Miner API | `jiangxi-miner-api` | 仅江西 Docker 网络内部 |
| MySQL | `jiangxi-mysql` | 仅江西 Docker 网络内部 |

三个公开端口均只绑定宿主机 `127.0.0.1`。不得为 Miner API 或 MySQL 增加宿主机端口映射，也不得改为全网卡监听。

## 2. 项目隔离

江西根目录为 `D:\项目\JiangXi\JiangXi-Platform`。云南工程及其代码、容器、镜像、命名卷、数据库和运行数据保持不变；江西编排不连接、不挂载、不复用这些资源。

江西应用运行镜像为 `jiangxi-runtime:current`，可选 GPU 镜像为 `jiangxi-runtime:gpu`。应用容器统一使用 `jiangxi-` 前缀，命名卷为：

```text
jiangxi_backend_static
jiangxi_mysql_data
jiangxi_hf_cache
jiangxi_miner_outputs
jiangxi_miner_tiles
```

MySQL 基础镜像由 `.env.example` 中的 `MYSQL_IMAGE` 指定；其容器与数据卷仍属于江西命名空间。
Compose 显式设置 `DB_BACKEND=mysql`，避免继承运行镜像的单机 SQLite 配置。

## 3. 认证与导航

- 会话 Cookie：`jiangxi_session`
- Cookie 由同一个江西业务后端签发，Miner 与解译前端共享登录状态。
- 任一江西前端退出后，服务端会话失效，两端均需重新登录。
- 江西会话不覆盖云南会话，云南登录状态也不作为江西认证依据。
- Miner 的“解译平台”入口固定指向 `4174/#/segmentation`。
- 解译平台的“返回矿山地图”入口固定指向 `4173/#/map`。
- 缺少入口地址配置时显示明确错误并禁用跳转，不执行地址或路由回退。

## 4. 业务执行方式

江西地物分类采用同步批量推理，默认使用 CPU。光谱指数计算同样由江西后端直接处理并返回结果。江西前端不使用异步任务查询接口，不提供自动设备选择，也不承诺 GPU 异常时回退 CPU。

`docker-compose.gpu.yml` 只是可选技术覆盖文件：它为后端和 Miner API 指定 `jiangxi-runtime:gpu` 并声明 GPU 资源。该文件不改变默认 CPU 口径，也不构成自动调度或异常回退能力说明。

## 5. 数据与持久化

江西权威种子数据：

```text
docker/standalone/runtime_data/Jiangxi_NaturalMine.kmz
docker/standalone/runtime_data/348个图斑.shp
docker/standalone/runtime_data/348个图斑.shx
docker/standalone/runtime_data/348个图斑.dbf
docker/standalone/runtime_data/348个图斑.prj
miner/data/348图斑_TableMERNet无图像预测结果.xlsx
```

默认从上述江西种子重建独立数据库和运行态。不默认迁移旧数据库、缓存或推理结果。仅允许迁移人工确认属于江西的成果，并记录原始来源、目标位置和校验结果；细则见 [legacy_data_migration.md](legacy_data_migration.md)。

## 6. 编排入口

- 默认 CPU：`docker-compose.prod.yml`
- 可选 GPU 资源覆盖：`docker-compose.gpu.yml`
- 环境变量模板：`.env.example`

标准启动与验证见 [offline_deployment_guide.md](offline_deployment_guide.md)，重启排障见 [docker_restart_guide.md](docker_restart_guide.md)。
