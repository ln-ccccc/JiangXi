# 江西省矿山生态修复智能监测平台用户手册

适用范围：本机或受控内网中的江西独立工程。项目根目录为 `D:\项目\JiangXi\JiangXi-Platform`。

## 1. 启动前准备

1. 从根目录复制 `.env.example` 为未跟踪的 `.env`。
2. 替换 `ADMIN_PASSWORD`、`SECRET_KEY`、`MYSQL_PASSWORD` 和 `MYSQL_ROOT_PASSWORD` 的占位符。
3. 确认江西权威种子数据存在：
   - `docker/standalone/runtime_data/Jiangxi_NaturalMine.kmz`
   - `docker/standalone/runtime_data/348个图斑.shp` 及同名配套文件
   - `miner/data/348图斑_TableMERNet无图像预测结果.xlsx`
4. 使用默认 CPU 编排启动：

```powershell
Set-Location 'D:\项目\JiangXi\JiangXi-Platform'
Copy-Item .env.example .env
# 编辑 .env，替换全部密码和密钥占位符。
docker compose --env-file .env -f docker-compose.prod.yml config
docker compose --env-file .env -f docker-compose.prod.yml up -d
docker compose --env-file .env -f docker-compose.prod.yml ps
```

停止服务使用：

```powershell
docker compose --env-file .env -f docker-compose.prod.yml down
```

不要附加 `-v`，否则会删除江西命名卷。

## 2. 访问入口

| 功能 | 地址 |
| --- | --- |
| Miner 地图 | `http://127.0.0.1:4173/#/map` |
| 江西解译平台 | `http://127.0.0.1:4174/#/segmentation` |
| 业务后端 | `http://127.0.0.1:5178` |

公开端口只绑定 `127.0.0.1`。Miner API 与 MySQL 仅在江西 Docker 网络内部，不提供宿主机访问地址。

## 3. 登录与跨前端会话

在任一江西前端输入 `.env` 中的管理员账号和密码。两个前端连接同一后端，并使用 `jiangxi_session`：

- 登录 Miner 后进入江西解译平台，不需要再次输入密码。
- 登录江西解译平台后返回 Miner，同样保持会话。
- 在任一前端退出后，两端会话同时失效。
- 江西登录状态不读取或覆盖云南登录状态。

首次从旧 Cookie 命名空间切换到 `jiangxi_session` 时，需要重新登录一次。

## 4. Miner 地图

打开 `http://127.0.0.1:4173/#/map` 后，地图使用江西矿区数据。默认矿区边界来自 `Jiangxi_NaturalMine.kmz`，图斑数据来自 `348个图斑.shp` 及其配套文件。

点击矿山图斑时，生态诊断信息使用 `348图斑_TableMERNet无图像预测结果.xlsx`。图斑与工作簿按项目现有受控标识关联；缺少关联数据时应显示缺失状态，不从其他省份数据或旧缓存补值。

页面中的“解译平台”入口只打开江西解译平台。若入口配置缺失，按钮会禁用并显示错误，不会自动跳往其他地址。

## 5. 江西解译平台

江西解译平台包含两类业务：

### 地物分类

1. 选择或上传受支持的数据源。
2. 设置当前页面提供的分析参数。
3. 提交同步批量分析。
4. 等待本次 CPU 请求完成。
5. 查看结果预览与历史结果。

### 光谱指数

1. 选择或上传数据源。
2. 选择页面提供的光谱指数与波段参数。
3. 提交计算。
4. 查看统计、预览与历史结果。

江西执行方式固定为同步 CPU。页面不查询异步任务，不提供自动设备选择或 GPU 异常回退。

解译平台中的“返回矿山地图”只返回 `http://127.0.0.1:4173/#/map`。缺少 Miner 地址配置时会报错，不使用替代地址。

## 6. 地物分类模型状态

若页面提示“江西地物分类模型未配置”，需要管理员在受控江西模型目录中提供 CPU 兼容的六类配置、权重和元数据。元数据必须声明江西、固定六类顺序并绑定配置/权重 SHA-256；系统还会校验模型加载后的实际类别，不会调用云南模型作为回退。

## 7. 数据与成果迁移

江西数据库从权威种子重建。默认不迁移旧数据库、缓存、会话、瓦片或推理结果。

只有人工确认属于江西的成果才可迁移，并必须记录：

- 原始来源
- 江西目标位置
- 文件大小和 SHA-256 校验值
- 迁移人、复核人和验证结果

详细规则见 [legacy_data_migration.md](legacy_data_migration.md)。不得连接、挂载或修改云南工程资源。

## 8. 常见问题

| 现象 | 处理方式 |
| --- | --- |
| Compose 提示缺少变量 | 从 `.env.example` 重建未跟踪的 `.env`，替换全部必填占位符。 |
| `4173`、`4174` 或 `5178` 无法访问 | 运行 `docker compose ... ps`，再查看对应 `jiangxi-*` 容器日志和本机端口占用。 |
| 从 Miner 进入解译平台仍要求登录 | 核对两个前端是否连接同一 `5178` 后端、Cookie 是否为 `jiangxi_session`。 |
| 入口按钮禁用 | 核对 `VITE_GEOVIEW_URL`、`VUE_APP_MINER_URL` 和 `VUE_APP_BACKEND_URL`。 |
| 江西矿区未加载 | 检查 KMZ、Shapefile 及配套文件是否位于 `/app/runtime_data`。 |
| 生态诊断缺失 | 检查权威工作簿是否挂载到 `/app/miner/data/`，并核对图斑标识。 |
| 分析执行时间较长 | 江西使用同步 CPU，请等待当前请求结束；不要按异步任务或 GPU 回退流程排查。 |

## 9. 运维边界

- 不提交 `.env`、真实凭据、数据库、日志、缓存和推理结果。
- 所有宿主机端口保持绑定 `127.0.0.1`。
- 不为 Miner API 或 MySQL 增加宿主机端口。
- 不停止、删除、挂载或修改云南工程资源。
- 生产或交付验收必须按实际执行情况记录；未执行的分类、指数或浏览器流程应明确标为未验证。
