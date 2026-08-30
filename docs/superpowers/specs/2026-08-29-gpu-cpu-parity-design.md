# GPU 与 CPU 使用体验一致性设计

## 目标

让江西 GPU standalone 在页面入口、登录、项目管理、地图跳转和持久化数据行为上与 CPU standalone 使用相同的默认地址和流程；仅推理设备与底层 CUDA 运行时不同。

## 已确认根因

1. GPU 容器被临时映射到 `4673/4674/5678`，但主前端的既有默认地址是 `4173/4174/5178`。
2. `backend/app.py` 在后端启动时重写 `frontend/.env`，覆盖了 `docker/write-runtime-env.py` 生成的公开地址配置。
3. GPU 容器创建时从环境文件继承了 `DB_BACKEND=mysql`；standalone 启动脚本会在服务进程内改为 SQLite，但独立 `docker exec` 进程仍会看到 MySQL 配置。

## 设计决策

- GPU standalone 固定使用与 CPU 一致的发布端口：地图 `4173`、主前端 `4174`、后端 `5178`。
- standalone 模式下，`docker/write-runtime-env.py` 是唯一允许写入前端运行时 `.env` 的组件；`backend/app.py` 不再覆盖它。
- standalone 启动脚本和 Docker 运行命令都明确使用 `DB_BACKEND=sqlite` 与 `/app/runtime_data/jiangxi.sqlite3`。
- 复用现有 GPU runtime volume，不删除 SQLite、种子标记或推理结果。
- 管理员密码只通过运行时环境变量提供；不写入源码、文档或日志。

## 验收

- `http://127.0.0.1:4174/` 的登录请求到达 `http://127.0.0.1:5178/`。
- `http://127.0.0.1:4173/#/map`、`http://127.0.0.1:4174/#/segmentation` 和后端健康检查均可访问。
- GPU 后端实际进程环境为 SQLite，CUDA 设备为 `cuda:0`。
- 348 条 TBBH、资产 manifest 和现有推理结果在重建后仍存在。
