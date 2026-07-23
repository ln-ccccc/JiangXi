# 江西交付清单

- [ ] 使用 `.env.example` 创建未跟踪的 `.env`，替换所有管理员、应用和数据库密钥。
- [ ] 将江西运行数据放入 `docker/standalone/runtime_data`，确认包含 Shapefile 全部配套文件、KMZ 与 `Mine.csv`。
- [ ] 执行 `docker compose -f docker-compose.prod.yml config`，确认未显示 Windows 宿主机路径且未发布 MySQL 端口。
- [ ] 运行 `miner` 的 `format:check`、`lint`、`test`、`build`，以及后端 Ruff 与单元测试。
- [ ] 启动后使用管理员账号完成登录、江西图斑加载、项目导出、备份恢复和 KML ROI 推理的最小人工验收。

已知限制：这是单管理员内网系统；数据、备份和推理结果保存在容器或服务端受控目录，不支持客户端指定任意输出目录。
