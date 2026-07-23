# 管理员登录说明

## 环境变量

```text
ADMIN_USERNAME=admin
ADMIN_PASSWORD=必须显式设置强密码
```

- 管理员用户名固定为 `admin`。
- 登录密码只从服务端环境变量 `ADMIN_PASSWORD` 读取。
- 忘记密码时，更新 `ADMIN_PASSWORD` 后重建 `backend`、`miner-api`、`miner-web` 容器即可重置。
- `docker compose` 未提供 `ADMIN_PASSWORD` 时，服务不会启动。

## 认证边界

- 浏览器只保存服务端会话 cookie。
- 不把密码、JWT 或长期 token 写入 `localStorage/sessionStorage`。
- `miner` 负责把浏览器 cookie 转发给 `backend`，由 `backend` 统一鉴权。

## 认证接口

- `POST /api/auth/login`
- `GET /api/auth/session`
- `POST /api/auth/logout`

## 登录后才能访问

- `/api/projects`
- `/api/stats`
- `/api/geojson`
- `/api/mines/*`
- `/api/kml/*`
- `/api/inference/*`
- `/change-matrix-outputs/*`

## Docker 联调

```powershell
$env:APP_IMAGE="geoview-runtime:current"
$env:ADMIN_PASSWORD="<强密码>"
$env:SECRET_KEY="<临时或正式密钥>"
$env:MINER_DEFAULT_KMZ_PATH="D:\项目\江西数据\Jiangxi_NaturalMine.kmz"
$env:MINER_MAP_PROVIDER="gaode"
docker compose -f docker-compose.prod.yml up -d --force-recreate backend miner-api miner-web
```

## 最小验收

- 未登录打开 `http://127.0.0.1:4000/#/projects` 时只显示登录页。
- 使用 `admin + ADMIN_PASSWORD` 登录成功后进入江西项目工作台。
- 已登录时可以进入 `#/map`。
- 工作台默认项目、地图筛选项和主流程文案应体现江西口径，不再出现“云南 / 大理 / 曲靖”。
- 如按上述联调脚本启动，浏览器网络面板中应能看到 `gaode` 在线卫星底图请求。
- 退出登录后再次访问业务 API 返回 `401`。
