# 江西独立工程开发指南

项目根目录固定为：

```text
D:\项目\JiangXi\JiangXi-Platform
```

本文只描述江西工程。云南工程及其运行资源不属于本仓库，开发、测试和部署时不得连接、挂载或复用。

## 1. 目录职责

- `miner/`：江西 Miner 地图前端与 Miner API 源码。
- `frontend/`：江西解译前端，包含地物分类与光谱指数页面。
- `backend/`：江西业务后端、同步批量解译与结果服务。
- `docker/`：容器启动脚本及江西运行种子数据。
- `docs/`：开发、部署、运维和验收文档。
- `docker-compose.prod.yml`：江西固定 CPU 部署编排。

## 2. 运行契约

公开入口只有：

- Miner 地图：`http://127.0.0.1:4173/#/map`
- 江西解译平台：`http://127.0.0.1:4174/#/segmentation`
- 业务后端：`http://127.0.0.1:5178`

所有公开端口只绑定 `127.0.0.1`。Miner API 与 MySQL 仅允许通过 Compose 内部网络访问。应用容器、命名卷和运行镜像使用 `jiangxi-*` 命名空间。

两个江西前端连接同一业务后端，Cookie 名固定为 `jiangxi_session`。任一前端完成登录后，另一前端复用同一会话；退出登录后两端会话同时失效。

前端入口必须由以下变量显式配置：

```text
DB_BACKEND=mysql
VITE_GEOVIEW_URL=http://127.0.0.1:4174/
VUE_APP_MINER_URL=http://127.0.0.1:4173/
VUE_APP_BACKEND_URL=http://127.0.0.1:5178/
```

`DB_BACKEND=mysql` 必须显式保留，用于覆盖运行镜像中的单机 SQLite 默认值，确保独立栈连接 `jiangxi-mysql` 与 `jiangxi_mysql_data`。

缺少入口配置时，界面应禁用入口并显示错误，不得回退到其他项目、其他端口或其他路由。

## 3. 功能边界

- 江西解译保留地物分类与光谱指数计算。
- 默认执行方式为同步批量请求，前端等待本次请求完成。
- 设备固定为 CPU，不接入异步任务查询、自动设备选择或 GPU 异常回退流程。
- 地物分类资产必须位于 `JIANGXI_MMSEG_MODEL_ROOT` 受控目录内，通过配置、权重、元数据路径和可选的 `JIANGXI_MMSEG_SOURCE_ROOT` 指向江西专用模型；元数据绑定文件 SHA-256，加载后再校验实际六类顺序和分类头数量；任一项不匹配时明确失败，不使用其他省份模型。

## 4. 权威数据

默认种子数据位于 `docker/standalone/runtime_data/`：

- `Jiangxi_NaturalMine.kmz`
- `348个图斑.shp` 及同名 `.shx`、`.dbf`、`.prj`

生态诊断权威工作簿位于：

```text
miner/data/348图斑_TableMERNet无图像预测结果.xlsx
```

不得用其他省份数据、旧缓存或历史推理结果作为江西缺失数据的自动回退。

## 5. 本地质量命令

Miner：

```powershell
Set-Location 'D:\项目\JiangXi\JiangXi-Platform\miner'
npm ci
npm run verify
```

江西解译前端：

```powershell
Set-Location 'D:\项目\JiangXi\JiangXi-Platform\frontend'
npm ci
npm run test:backend-url
npm run test:navigation
npm run test:ui
npm run build
```

后端：

```powershell
Set-Location 'D:\项目\JiangXi\JiangXi-Platform\backend'
python -m unittest discover -p 'test_*.py'
```

部署配置：

```powershell
Set-Location 'D:\项目\JiangXi\JiangXi-Platform'
Copy-Item .env.example .env
# 编辑未跟踪的 .env，替换全部密码和密钥占位符。
docker compose --env-file .env -f docker-compose.prod.yml config
```

测试结果必须按实际执行情况记录；没有启动容器或没有执行浏览器流程时，不得写成已通过。

## 6. 修改与交付边界

- 不修改云南工程，不复用其容器、镜像、卷、数据库或数据路径。
- 不提交 `.env`、密码、密钥、数据库、缓存、日志和推理结果。
- API、环境变量、部署命令或数据目录发生变化时，同步更新对应文档。
- 每次交付列出修改文件、实际验证命令、结果、未验证项与风险。

开发规范见 [development_standard.md](development_standard.md)，交付前核对 [delivery_checklist.md](delivery_checklist.md)。
