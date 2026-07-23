# 江西独立工程概览

## 1. 项目定位

`D:\项目\JiangXi\JiangXi-Platform` 是江西省矿山生态修复智能监测平台的独立根仓库，包含：

- Miner 地图端
- 江西解译前端
- 江西业务后端
- Miner API
- MySQL 与 Docker 编排
- 江西权威种子数据和受控结果目录

云南工程及其代码、容器、镜像、命名卷、数据库和运行数据保持不变。江西部署不连接、不挂载、不复用这些资源。

## 2. 公开入口

- Miner 地图：`http://127.0.0.1:4173/#/map`
- 江西解译平台：`http://127.0.0.1:4174/#/segmentation`
- 业务后端：`http://127.0.0.1:5178`

公开端口全部只绑定 `127.0.0.1`。Miner API 与 MySQL 只在江西 Docker 网络内部开放。

## 3. 身份与导航

两个江西前端连接同一个江西业务后端，通过 `jiangxi_session` 共享登录会话。登录任一前端后可直接进入另一前端；退出登录后两端同时失效。

Miner 只跳转到江西解译入口，解译平台只返回江西 Miner。入口配置缺失时显示错误并禁用入口，不回退到其他项目或其他端口。

## 4. 功能边界

- 地物分类：同步批量推理，默认 CPU。
- 光谱指数：保留现有计算、预览和历史结果能力。
- 不使用异步任务查询。
- 不提供自动设备选择。
- 不提供 GPU 异常时自动回退 CPU。

`docker-compose.gpu.yml` 是可选技术覆盖文件，仅声明 GPU 镜像与资源；默认部署仍使用 `docker-compose.prod.yml` 和 `jiangxi-runtime:current`。

## 5. 江西权威数据

- `docker/standalone/runtime_data/Jiangxi_NaturalMine.kmz`
- `docker/standalone/runtime_data/348个图斑.shp` 及同名配套文件
- `miner/data/348图斑_TableMERNet无图像预测结果.xlsx`

数据库从江西权威种子重建。旧数据库、缓存和推理结果不默认迁移；只有人工确认属于江西的成果才可按迁移规则登记后导入。

## 6. Docker 命名空间

- 应用镜像：`jiangxi-runtime:current`；可选 `jiangxi-runtime:gpu`
- 容器：`jiangxi-backend`、`jiangxi-frontend`、`jiangxi-miner-api`、`jiangxi-miner-web`、`jiangxi-mysql`
- 命名卷：`jiangxi_backend_static`、`jiangxi_mysql_data`、`jiangxi_hf_cache`、`jiangxi_miner_outputs`、`jiangxi_miner_tiles`

部署步骤见 [offline_deployment_guide.md](offline_deployment_guide.md)，系统边界见 [system_guide.md](system_guide.md)。
