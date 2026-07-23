# 江西 Docker 调试与受控热修

本文适用于 `D:\项目\JiangXi\JiangXi-Platform` 的 `docker-compose.prod.yml`。只排查江西容器，不操作云南工程或资源。

## 1. 状态与日志

```powershell
Set-Location 'D:\项目\JiangXi\JiangXi-Platform'
docker compose --env-file .env -f docker-compose.prod.yml ps
docker ps -a --filter 'name=jiangxi-' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
docker logs --tail 200 jiangxi-backend
docker logs --tail 200 jiangxi-frontend
docker logs --tail 200 jiangxi-miner-api
docker logs --tail 200 jiangxi-miner-web
docker logs --tail 120 jiangxi-mysql
```

## 2. 容器内只读检查

```powershell
docker exec jiangxi-backend bash -lc 'python -V; ls -lah /app/backend; ls -lah /app/runtime_data'
docker exec jiangxi-miner-api bash -lc 'node -v; ls -lah /app/miner; ls -lah /app/runtime_data'
docker exec jiangxi-mysql sh -lc 'mysqladmin ping -h 127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" --silent'
```

重点确认：

- `/app/runtime_data/Jiangxi_NaturalMine.kmz` 存在。
- `/app/runtime_data/348个图斑.shp` 及配套文件存在。
- `/app/miner/data/348图斑_TableMERNet无图像预测结果.xlsx` 存在。
- 数据路径不指向其他省份工程。

## 3. 公开入口检查

```powershell
curl.exe -I 'http://127.0.0.1:4173/'
curl.exe -I 'http://127.0.0.1:4174/'
curl.exe -I 'http://127.0.0.1:5178/'
```

浏览器使用：

- `http://127.0.0.1:4173/#/map`
- `http://127.0.0.1:4174/#/segmentation`

Miner API 与 MySQL 只通过容器健康检查和日志排查，不增加宿主机端口。

## 4. 配置与会话排查

```powershell
docker compose --env-file .env -f docker-compose.prod.yml config
docker exec jiangxi-backend bash -lc 'printf "%s\n" "$SESSION_COOKIE_NAME" "$CORS_ALLOWED_ORIGINS"'
```

预期 Cookie 名为 `jiangxi_session`，允许来源只包含 `127.0.0.1:4173` 与 `127.0.0.1:4174`。两个江西前端应连接同一后端；一个前端登录后进入另一个前端不应再次输入密码。

入口异常时核对：

```text
VITE_GEOVIEW_URL=http://127.0.0.1:4174/
VUE_APP_MINER_URL=http://127.0.0.1:4173/
VUE_APP_BACKEND_URL=http://127.0.0.1:5178/
```

缺少配置应出现明确错误；发现自动跳往其他地址时，应停止验收并修复配置或代码，不能用临时地址掩盖。

## 5. 受控重建

源码或配置修复必须先落到本仓库、完成审查和测试，再重建江西应用容器：

```powershell
docker compose --env-file .env -f docker-compose.prod.yml up -d --force-recreate backend frontend miner-api miner-web
docker compose --env-file .env -f docker-compose.prod.yml ps
```

不要把文件直接复制进运行容器作为正式交付；这种改动会在容器重建后丢失，也无法审计。

## 6. 默认 CPU 与可选 GPU

默认只使用 `docker-compose.prod.yml`，解译为同步 CPU。`docker-compose.gpu.yml` 仅供显式技术验证，不能据此宣称江西具备自动设备选择或 GPU 异常回退能力。

## 7. 安全边界

- 日志和诊断输出不得包含真实密码、密钥或完整 Cookie。
- 不使用 `down -v`、强制删除容器或清空数据库作为常规排障手段。
- 不连接、停止、删除或挂载云南工程资源。
- 所有宿主机端口保持绑定 `127.0.0.1`。
