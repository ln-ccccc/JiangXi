# 江西省矿山生态修复智能监测平台

本仓库是江西项目的独立工程，固定根目录为 `D:\项目\JiangXi\JiangXi-Platform`。工程包含 Miner 地图端、江西解译前端、业务后端、Miner API、MySQL 编排与江西权威种子数据。

## 公开入口

| 入口 | 地址 |
| --- | --- |
| Miner 地图 | `http://127.0.0.1:4173/#/map` |
| 江西解译平台 | `http://127.0.0.1:4174/#/segmentation` |
| 业务后端 | `http://127.0.0.1:5178` |

宿主机端口只绑定 `127.0.0.1`。Miner API 与 MySQL 仅在江西 Docker 网络内提供服务，不发布宿主机端口。江西应用镜像、容器和命名卷使用 `jiangxi-*` 命名空间；云南工程及其容器、镜像、数据卷、数据库和运行数据保持不变。

两个江西前端连接同一业务后端，并通过 `jiangxi_session` 共享登录会话。默认解译方式为同步 CPU；可选 GPU Compose 文件只声明运行资源，不代表自动设备选择或异常回退能力。

## 文档

- [部署指南](docs/offline_deployment_guide.md)
- [系统与隔离边界](docs/system_guide.md)
- [用户手册](docs/user_manual.md)
- [管理员登录](docs/admin_login.md)
- [重启与排障](docs/docker_restart_guide.md)
- [江西成果迁移规则](docs/legacy_data_migration.md)
- [交付检查清单](docs/delivery_checklist.md)
