# 江西 Docker 重启与排障

所有命令都在 `D:\项目\JiangXi\JiangXi-Platform` 执行，并使用未跟踪的 `.env`。命令不带 `-v`，不会删除江西命名卷。

## 1. 标准重启

```powershell
Set-Location 'D:\项目\JiangXi\JiangXi-Platform'
docker compose --env-file .env -f docker-compose.prod.yml restart
docker compose --env-file .env -f docker-compose.prod.yml ps
```

编排包含 `backend`、`frontend`、`miner-api`、`miner-web` 和 `mysql` 五个服务，对应容器均使用 `jiangxi-` 前缀。

## 2. 重建应用容器

只重建应用服务，保留 `jiangxi_mysql_data`、缓存与结果卷：

```powershell
docker compose --env-file .env -f docker-compose.prod.yml up -d --force-recreate backend frontend miner-api miner-web
docker logs --tail 200 jiangxi-backend
docker logs --tail 200 jiangxi-miner-api
docker compose --env-file .env -f docker-compose.prod.yml ps
```

## 3. 完整停止与重新启动

```powershell
docker compose --env-file .env -f docker-compose.prod.yml down
docker compose --env-file .env -f docker-compose.prod.yml config
docker compose --env-file .env -f docker-compose.prod.yml up -d --remove-orphans
docker compose --env-file .env -f docker-compose.prod.yml ps
```

不要附加 `-v`，除非已经单独备份且明确获准删除江西数据库和结果卷。

## 4. 公开入口检查

```powershell
curl.exe -I 'http://127.0.0.1:4173/'
curl.exe -I 'http://127.0.0.1:4174/'
curl.exe -I 'http://127.0.0.1:5178/'
```

浏览器验收地址：

- `http://127.0.0.1:4173/#/map`
- `http://127.0.0.1:4174/#/segmentation`

Miner API 与 MySQL 没有宿主机验证地址；使用 `docker compose ... ps` 与容器日志确认其健康状态。

## 5. 常见问题

### 容器名冲突

先只读定位占用者，不要直接删除未知容器：

```powershell
docker ps -a --filter 'name=jiangxi-' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
```

确认冲突容器属于本江西工程后，使用本工程 Compose 的 `down` 再重新启动。不得停止或删除云南容器。

### 配置展开失败

```powershell
Test-Path .env
Test-Path config.yaml
docker compose --env-file .env -f docker-compose.prod.yml config
```

若提示缺少变量，编辑 `.env` 并替换 `.env.example` 中对应占位符；不要把真实密码写回模板或提交到 Git。

### 页面无法访问

```powershell
docker compose --env-file .env -f docker-compose.prod.yml ps
docker logs --tail 200 jiangxi-miner-web
docker logs --tail 200 jiangxi-frontend
docker logs --tail 200 jiangxi-backend
```

确认端口只绑定 `127.0.0.1`，且本机没有其他进程占用 `4173`、`4174`、`5178`。

### 入口按钮不可用

核对 `.env`：

```text
VITE_GEOVIEW_URL=http://127.0.0.1:4174/
VUE_APP_MINER_URL=http://127.0.0.1:4173/
VUE_APP_BACKEND_URL=http://127.0.0.1:5178/
```

缺少配置时应用会明确报错，不会自动跳转到其他项目地址。
