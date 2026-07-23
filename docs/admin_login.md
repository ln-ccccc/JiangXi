# 江西管理员登录说明

## 1. 环境变量

从 `.env.example` 创建未跟踪的 `.env`，使用占位符替换真实部署值：

```text
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<管理员强密码>
SECRET_KEY=<随机应用密钥>
SESSION_COOKIE_NAME=jiangxi_session
SESSION_COOKIE_SECURE=false
```

本机 HTTP 验收时 `SESSION_COOKIE_SECURE=false`；若后续经反向代理提供 HTTPS，应按部署环境评估并显式调整。真实密码和密钥不得写入文档或提交到版本库。

## 2. 会话边界

- Miner 与江西解译前端连接同一个江西业务后端。
- 会话 Cookie 名固定为 `jiangxi_session`，浏览器不保存密码或长期令牌。
- 在任一江西前端登录后，进入另一江西前端不再输入密码。
- 在任一江西前端退出后，服务端会话失效，两端均需重新登录。
- 江西会话与云南会话相互独立，不覆盖、不复用。

Cookie 命名空间首次切换后需要重新登录一次；之后按上述共享规则工作。

## 3. 登录接口

- `POST /api/auth/login`
- `GET /api/auth/session`
- `POST /api/auth/logout`

业务 API 由后端统一鉴权。Miner API 通过江西 Docker 内部网络访问同一后端，不单独发布宿主机端口。

## 4. 启动或重置密码

```powershell
Set-Location 'D:\项目\JiangXi\JiangXi-Platform'
docker compose --env-file .env -f docker-compose.prod.yml config
docker compose --env-file .env -f docker-compose.prod.yml up -d --force-recreate backend miner-api
```

忘记密码时，在未跟踪的 `.env` 中更新 `ADMIN_PASSWORD`，再重建 `backend` 与 `miner-api`。不要修改 `.env.example` 保存真实密码。

## 5. 最小认证验收

1. 未登录打开 `http://127.0.0.1:4173/#/map`，确认进入江西登录流程。
2. 使用 `.env` 中的管理员账号登录。
3. 从 Miner 打开 `http://127.0.0.1:4174/#/segmentation`，确认不再次要求密码。
4. 返回 `http://127.0.0.1:4173/#/map`，确认会话仍有效。
5. 在任一前端退出，确认两个前端均失去会话。
6. 确认浏览器 Cookie 名为 `jiangxi_session`，且没有覆盖云南 Cookie。

## 6. 入口配置异常

以下地址必须显式配置：

```text
VITE_GEOVIEW_URL=http://127.0.0.1:4174/
VUE_APP_MINER_URL=http://127.0.0.1:4173/
VUE_APP_BACKEND_URL=http://127.0.0.1:5178/
```

缺少地址时，入口应禁用并显示错误；不得自动跳转到其他项目、旧端口或替代路由。
