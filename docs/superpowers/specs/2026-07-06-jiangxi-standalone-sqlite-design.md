# 江西单镜像 SQLite 交付设计文档

## 1. 背景

当前项目目录 `D:\项目\JiangXi\YunNan_prechange_20260703_223508` 已完成以下关键工作：

- 正式交付包恢复
- 江西区域化代码改造
- 江西空库重建与业务数据导入
- `/api/geojson` 切换到江西面图斑源
- 江西单镜像方案的第一轮构建链路搭建

在上一轮“应用 + 数据库单镜像”方案验证中，已确认以下事实：

- 单镜像 `build` 已成功
- 单镜像 `run` 失败
- 失败根因不是启动脚本，而是基础镜像 `geoview-runtime:split-clean` 中不存在 `mysqld`
- 当前单镜像若继续坚持内置 MySQL，需要额外在镜像中安装数据库服务端

用户随后提出新的问题：“这里能不用数据库吗？”

经分析后，结论是：

- 不能直接把数据库完全去掉且不改业务代码
- 但可以把当前依赖的 MySQL 切换为 SQLite 单文件数据库
- 用户已确认采用“SQLite 单文件方案 + 保留完整业务主流程”

因此，本轮设计目标不再是把 MySQL 服务端塞进江西单镜像，而是：

- 保留当前完整业务能力
- 将单镜像运行时中的数据库依赖从 MySQL 改为 SQLite 单文件
- 继续保持江西专用单镜像交付模式

## 2. 用户已确认约束

本轮已确认的关键约束如下：

- 继续采用江西专用单镜像交付
- 不再要求镜像内运行 MySQL 服务端
- 保留完整业务能力，而不是退化为只读演示版
- 继续保留：
  - 登录
  - 项目列表
  - 江西默认项目
  - 主体矿山列表
  - 图斑明细
  - 江西面图斑 GeoJSON
- 继续只对外暴露业务端口：
  - `4000`
  - `5008`

## 3. 目标

本次设计目标是构建一个“江西单镜像 SQLite 交付物”，满足以下要求：

- 单个镜像内只运行应用进程，不再运行 MySQL 服务端
- 后端生产环境改用 SQLite 单文件数据库
- 首次启动时自动创建 SQLite 数据库文件并完成表结构初始化
- 首次启动时自动完成江西业务数据导入
- `/api/projects` 返回江西默认项目
- `/api/geojson` 返回江西面图斑
- 登录、项目、主体、图斑等主流程保持可用
- 宿主只需要访问 `4000` 与 `5008`

## 4. 非目标

本次设计不包含以下内容：

- 不实现 MySQL 与 SQLite 双后端长期并行支持
- 不把数据库完全改造成 JSON/CSV 文件直读
- 不重构所有写操作为纯文件模式
- 不在本轮做多租户、多省切换
- 不在本轮做镜像极限瘦身

## 5. 当前系统事实

### 5.1 配置事实

当前后端配置集中在：

- `backend/applications/configs/config.py`

已确认：

- `testing` 环境已经使用 `sqlite:///:memory:`
- `production` 环境当前默认使用 `mysql+pymysql://...`

这说明：

- 现有项目并非完全不支持 SQLite
- 当前阻塞点主要是“生产环境配置默认绑死 MySQL”

### 5.2 初始化事实

应用启动入口位于：

- `backend/applications/__init__.py`

已确认：

- 启动时会执行 `db.create_all()`
- 非测试环境会执行初始化脚本

这意味着：

- 只要把生产数据库 URI 正确切到 SQLite
- 应用已有能力在首次启动时自动建表

### 5.3 当前单镜像事实

当前单镜像第一轮已具备：

- `docker/standalone/Dockerfile.jiangxi`
- `docker/standalone/start-jiangxi-standalone.sh`
- `docker/standalone/seed-jiangxi-runtime.sh`
- `docker/standalone/runtime_data/*`

但这套链路仍然假定容器内存在 MySQL 服务端，因此需要收敛为 SQLite 方案。

## 6. 方案对比

### 6.1 方案 S1：生产环境改为 SQLite 单文件

做法：

- 在生产配置中增加 SQLite 运行模式
- 单镜像把 SQLite 数据库文件放在运行时目录
- 首次启动时自动建库、建表、初始化管理员、导入江西数据

优点：

- 改造量最小
- 能保留现有 SQLAlchemy 模型和接口
- 最适合单镜像交付
- 不需要在镜像内安装 `mysqld`

缺点：

- 仍然使用数据库，只是数据库从服务端模式变为单文件模式

### 6.2 方案 S2：同时支持 MySQL 与 SQLite

做法：

- 增加 `DB_BACKEND=mysql|sqlite`
- 单镜像默认走 SQLite，但代码保留双模式

优点：

- 灵活

缺点：

- 增加长期维护复杂度
- 对当前江西专用交付没有直接收益

### 6.3 方案 S3：完全去数据库

做法：

- 登录、项目、主体、图斑全部改为文件直读

优点：

- 彻底摆脱数据库依赖

缺点：

- 需要重写大量现有业务逻辑
- 不适合当前阶段

### 6.4 结论

本轮采用 `S1`，即“江西单镜像 + SQLite 单文件 + 保留完整业务”。

## 7. 总体设计

### 7.1 数据库策略

单镜像运行时不再启动 MySQL 服务端。

改为使用 SQLite 单文件：

- 建议路径：`/app/runtime_data/jiangxi.sqlite3`

运行逻辑如下：

- 若数据库文件不存在，则首次创建
- 应用启动后执行 `db.create_all()`
- 初始化管理员账号
- 执行江西导入脚本
- 后续复用同一个 SQLite 文件

### 7.2 运行进程

单镜像保留以下应用进程：

- `backend`
- `frontend`
- `miner-api`
- `miner-web`

不再启动：

- `mysqld`

### 7.3 对外端口

单镜像仍仅对外暴露：

- `4000`
- `5008`

以下端口仅保留容器内逻辑意义，不对宿主暴露：

- `3000`
- `8000`

## 8. 配置设计

### 8.1 生产环境数据库配置

需要把 `production` 数据库配置改成可切到 SQLite。

推荐新增环境变量：

- `DB_BACKEND=sqlite`
- `SQLITE_PATH=/app/runtime_data/jiangxi.sqlite3`

推荐规则：

- 当 `DB_BACKEND=sqlite` 时，`SQLALCHEMY_DATABASE_URI` 使用：
  - `sqlite:////app/runtime_data/jiangxi.sqlite3`
- 当未显式声明时，江西单镜像默认走 SQLite

### 8.2 不再需要的外部数据库配置

单镜像模式下，用户不再需要提供：

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USERNAME`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

仍应保留的关键环境变量：

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `SECRET_KEY`
- `BACKEND_PORT`
- `MINER_FRONTEND_PORT`

## 9. 启动链设计

### 9.1 启动顺序

单镜像建议按以下顺序启动：

1. 检查 `runtime_data` 中的江西数据文件是否存在
2. 检查 `jiangxi.sqlite3` 是否存在
3. 若不存在，则进入首次初始化流程
4. 设置 SQLite 运行环境变量
5. 启动 `backend`
6. 启动 `frontend`
7. 启动 `miner-api`
8. 启动 `miner-web`

### 9.2 首次初始化流程

首次初始化应包括：

1. 使用 SQLite 连接创建业务表
2. 初始化管理员账号
3. 执行江西空库重建导入：
   - `Mine.csv`
4. 校验 `/api/projects` 已生成江西默认项目
5. 保留一个初始化完成标记，避免每次启动重复导入

### 9.3 幂等性

必须避免每次容器启动都重复重建数据。

建议采用双重判定：

- SQLite 文件是否已存在
- 初始化 marker 是否已存在

只有首次运行时才执行江西初始化导入。

## 10. 数据文件策略

### 10.1 必带文件

单镜像运行时仍需打包或带入以下数据：

- `Mine.csv`
- `348个图斑.shp`
- `348个图斑.shx`
- `348个图斑.dbf`
- `348个图斑.prj`
- `Jiangxi_NaturalMine.kmz`（如现有链路仍需兼容）

### 10.2 SQLite 文件

`jiangxi.sqlite3` 不建议在构建时提前固化为最终交付态数据库。

推荐策略：

- 运行时首次生成
- 写入容器运行目录
- 通过数据卷或容器内目录持久化

理由：

- 降低构建时耦合
- 便于重置与重新导入
- 更容易判断首次初始化逻辑是否正常

## 11. 单镜像结构调整

### 11.1 Dockerfile

`docker/standalone/Dockerfile.jiangxi` 需要调整为：

- 不再安装或依赖 MySQL 服务端
- 保留应用运行时环境
- 复制江西数据文件到 `/app/runtime_data`
- 设置 SQLite 模式默认环境变量

### 11.2 standalone 启动脚本

`docker/standalone/start-jiangxi-standalone.sh` 需要调整为：

- 去掉 `init-mysql-runtime.sh`
- 改为调用 SQLite 初始化与江西首次导入逻辑
- 启动后交给统一应用 entrypoint 守护

### 11.3 seed 脚本

`docker/standalone/seed-jiangxi-runtime.sh` 需要调整为：

- 不再导出 MySQL 连接变量
- 改为导出 SQLite 连接变量
- 首次执行时运行：
  - `python seed_jiangxi_from_csv.py --csv-path /app/runtime_data/Mine.csv --config production --actor standalone`

## 12. 验收标准

单镜像交付完成后，应满足以下标准：

- `docker build` 成功
- `docker run` 成功
- 容器无需 `mysqld`
- `http://127.0.0.1:5008/` 可访问
- `http://127.0.0.1:4000/` 可访问
- 登录后项目列表为江西默认项目
- `/api/projects` 返回江西默认项目
- `/api/geojson` 返回江西面图斑
- 主流程不再出现云南口径

## 13. 风险与边界

- SQLite 并发能力弱于 MySQL，但对当前单机单镜像交付场景通常足够
- 个别原本依赖 MySQL 方言特性的 SQLAlchemy 行为需要在实施时验证
- 若某些初始化脚本显式使用 MySQL 环境变量，需要同步修正为 SQLite 模式
- 如果后续要恢复多用户并发生产环境部署，仍应重新评估是否回到 MySQL

## 14. 结论

本轮不再继续把 MySQL 服务端塞进江西单镜像，而是改为：

- 江西专用单镜像
- 完整业务保留
- 底层数据库切为 SQLite 单文件
- 首次启动自动建库、建表、初始化管理员和江西数据
- 继续只暴露 `4000`、`5008`

这条路径既满足“不要再内置数据库服务端”的诉求，也能保留当前江西业务系统的完整主流程，是当前阶段最稳妥的江西单镜像交付方案。
