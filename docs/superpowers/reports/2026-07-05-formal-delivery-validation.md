# 2026-07-05 正式交付验证报告

## 验证范围

- 验证目录：`D:\项目\JiangXi\YunNan_prechange_20260703_223508`
- 执行约束：仅在目标交付目录内执行验证与生成报告，未修改权威源目录
- 验证时间：2026-07-06
- 说明：本报告前半部分保留正式交付阶段的历史记录；若与江西区域化收口结果冲突，以文末“江西区域化补充验证（Task 4）”为准。

## 验证结论

| 模块 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- |
| backend | `backend\.venv_task_20260705\Scripts\python.exe backend\test_project_api.py` | 通过 | `2` 个测试全部通过 |
| miner | `npm run build` | 通过 | 成功产出 `dist`，存在大包体积告警 |
| miner | `npm test` | 通过 | `28` 个测试全部通过 |
| root | `docker compose -f docker-compose.prod.yml config` | 通过 | 使用交付编排文件并提供必填环境变量后渲染成功 |
| e2e startup | `docker compose -f docker-compose.prod.yml up -d --remove-orphans` | 通过 | 使用 `geoview-runtime:split-clean`、在线 `gaode` 地图模式拉起 5 个服务 |
| e2e browser | `4000 -> 3000` 联调验收 | 部分通过 | `miner` 登录和地图页正常，GeoView 登录页可打开，但当前业务数据仍为云南口径，且浏览器内 GeoView 登录跳转未完成 |

## 执行记录

### 1. backend

执行目录：`D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend`

执行命令：

```powershell
& 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend\.venv_task_20260705\Scripts\python.exe' 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend\test_project_api.py'
```

执行结果：

```text
Ran 2 tests in 0.668s

OK
```

附注：

- 运行过程中出现 `flask_sqlalchemy` 与 Flask 的弃用告警
- 当前不影响本次测试通过结论，但建议后续在依赖升级时统一清理

### 2. miner build

执行目录：`D:\项目\JiangXi\YunNan_prechange_20260703_223508\miner`

执行命令：

```powershell
npm run build
```

执行结果：

```text
vite v7.1.12 building for production...
✓ 678 modules transformed.
dist/index.html                     0.69 kB │ gzip:   0.43 kB
dist/assets/index-D1pgxJ_L.css     42.48 kB │ gzip:  12.25 kB
dist/assets/index-BwApDarJ.js   1,451.48 kB │ gzip: 483.16 kB
✓ built in 17.34s
```

附注：

- 构建成功
- Vite 报告主产物体积较大，提示后续可通过动态拆包或 `manualChunks` 优化

### 3. miner test

执行目录：`D:\项目\JiangXi\YunNan_prechange_20260703_223508\miner`

执行命令：

```powershell
npm test
```

执行结果：

```text
ℹ tests 28
ℹ pass 28
ℹ fail 0
ℹ duration_ms 486.1366
```

结论：

- 所有 `28` 个测试均通过

### 4. root docker compose config

执行目录：`D:\项目\JiangXi\YunNan_prechange_20260703_223508`

执行命令：

```powershell
$env:ADMIN_PASSWORD='Secret123!'
$env:SECRET_KEY='temporary-delivery-check-key'
docker compose -f docker-compose.prod.yml config > .trae\compose.rendered.final.yml
```

执行结果：

```text
命令退出码 0，成功生成 .trae\compose.rendered.final.yml
```

结果判定：

- 当前交付目录的正式 Compose 入口为 `docker-compose.prod.yml`
- 该编排文件要求提供 `ADMIN_PASSWORD` 与 `SECRET_KEY`
- 在显式指定 `-f docker-compose.prod.yml` 并提供必填环境变量后，Compose 渲染通过

### 5. clean environment startup

执行目录：`D:\项目\JiangXi\YunNan_prechange_20260703_223508`

执行命令：

```powershell
$env:APP_IMAGE='geoview-runtime:split-clean'
$env:MYSQL_IMAGE='registry.openanolis.cn/openanolis/mysql:8.0.30-8.6'
$env:ADMIN_PASSWORD='Secret123!'
$env:SECRET_KEY='temporary-delivery-check-key'
$env:OFFLINE_MAP_DIR=(Resolve-Path '.\offline_bundle\maps\dali').Path
$env:MINER_MAP_PROVIDER='gaode'
docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

执行结果：

```text
cugrs-miner-web   Up (healthy)
cugrs-miner-api   Up (healthy)
cugrs-frontend    Up (healthy)
cugrs-backend     Up (healthy)
cugrs-mysql       Up (healthy)
```

补充说明：

- 由于 `offline_bundle/images/geoview_runtime_current.tar` 为约 `10GB` 的离线镜像包，现场导入未在可接受时间内完成，因此本次真实启动验收使用本机已存在的 `geoview-runtime:split-clean` 运行时镜像完成
- 为满足“底图可使用在线地图”的验收要求，本次启动将 `MINER_MAP_PROVIDER` 设置为 `gaode`
- 本次未删除命名卷，只重建了项目容器

### 6. end-to-end acceptance

浏览器联调路径：

- 访问 `http://127.0.0.1:4000/`
- 使用 `admin / Secret123!` 登录矿山项目化监测平台
- 打开矿山地图页
- 从矿山地图页点击“解译平台”，跳转 `http://localhost:3000/login?redirect=%2Fsegmentation%23%2Fsegmentation`

浏览器与接口结果：

- `4000` 登录成功，工作台可见项目列表与“打开矿山地图”按钮
- `4000/#/map` 地图页可打开，筛选项和图层请求正常
- 网络请求显示在线高德卫星瓦片正在加载
- `5008/api/auth/login` 直接接口调用返回 `200`，说明 GeoView 后端认证接口可用
- `3000` 的 GeoView 登录页可打开，但浏览器内登录后未继续完成业务页跳转

当前业务口径判断：

- 地图页筛选项仅显示 `大理白族自治州`
- 工作台项目名称和监测区域仍为云南/大理口径
- 当前恢复包尚未完成“研究区域切换为江西，仅显示江西区域卫星影像”的改造

## 交付判断

- `backend` API 回归测试：通过
- `miner` 前端构建：通过
- `miner` 单元测试：通过
- 根目录 Docker Compose 交付编排校验：通过
- 5 个服务干净环境启动：通过
- 浏览器端到端联调：部分通过

总体判断：

- 当前目标目录已满足 `backend`、`miner` 与根目录交付编排的最终验证要求
- 目标目录已达到“按交付说明执行正式验证命令并拉起服务”的状态
- 但当前业务数据口径仍是云南，GeoView 浏览器端登录跳转也未完全闭环，因此还不能视为“江西研究区域版本”的最终验收通过包

## 后续建议

- 在正式部署或验收时，应按交付说明提供 `ADMIN_PASSWORD` 与 `SECRET_KEY` 等必填环境变量
- 如需进一步降低使用门槛，可后续补充 `.env.example` 或显式的环境变量模板文档
- 建议按文末最小联调脚本重新执行一次浏览器人工验收，重点检查主流程不再出现“云南 / 大理 / 曲靖”
- 如需继续优化正式交付体验，可为当前项目单独打包瘦身镜像，清理非江西/非交付必需内容，降低镜像体积和运行内存占用

## 江西区域化补充验证（Task 4）

本节对应江西区域化 Task 4 的文档收口、测试样例更新与最小验收脚本补充。以下结论基于本次最新执行结果，优先级高于前文历史记录。

### 1. 本次修改覆盖

- 交付文档：`docs/project_summary.md`、`docs/system_guide.md`、`docs/offline_deployment_guide.md`、`docs/admin_login.md`
- 设计文档：`docs/superpowers/specs/2026-07-05-jiangxi-regionalization-design.md`
- 测试样例：`miner/test/projectWorkspaceHelpers.test.js`

### 2. 回归执行结果

| 模块 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- |
| backend | `python -m unittest test_default_jiangxi_source.py -v` | 通过 | `2` 个测试 `OK` |
| backend | `python -m unittest test_legacy_project_migration.py -v` | 通过 | `2` 个测试 `OK`，伴随 Flask/SQLAlchemy 弃用告警 |
| backend | `python -m unittest test_project_api.py -v` | 通过 | `2` 个测试 `OK`，伴随 Flask/SQLAlchemy 弃用告警 |
| miner | `node --test test/defaultJiangxiSource.test.js test/projectRoutes.test.js test/projectWorkspaceHelpers.test.js` | 通过 | `5` 个测试全部通过，已覆盖江西默认源、项目路由与江西样例筛选 |
| miner | `npm run build` | 通过 | `679` 个模块转换成功，产物 `dist/assets/index-VckJC_7P.js` 约 `1.45 MB`，存在大包体积告警 |

### 3. 验证输出摘要

```text
backend/test_default_jiangxi_source.py: Ran 2 tests in 0.001s, OK
backend/test_legacy_project_migration.py: Ran 2 tests in 1.601s, OK
backend/test_project_api.py: Ran 2 tests in 0.768s, OK
miner node tests: pass 5, fail 0
vite build: built in 9.35s
```

### 4. 沙箱附加说明

- 上述 5 条命令在测试框架或构建工具层面均已输出 `OK` / `pass` / `built`。
- Trae 终端随后统一追加了 `TRAE Sandbox Error: hit restricted`，指向 `CryptnetUrlCache` 元数据路径访问限制。
- 该限制发生在成功输出之后，因此本次报告将这些命令判定为“业务验证通过，但工具层记录了附加沙箱限制”。

### 5. 江西最小联调验收脚本

```powershell
$env:APP_IMAGE='geoview-runtime:current'
$env:MYSQL_IMAGE='registry.openanolis.cn/openanolis/mysql:8.0.30-8.6'
$env:ADMIN_PASSWORD='<强密码>'
$env:SECRET_KEY='<临时或正式密钥>'
$env:MINER_MAP_PROVIDER='gaode'
$env:MINER_DEFAULT_KMZ_PATH='D:\项目\江西数据\Jiangxi_NaturalMine.kmz'
docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker compose -f docker-compose.prod.yml ps
```

### 6. 本轮结论

- 江西区域化相关交付文档已统一补充权威 KMZ 源、推荐联调变量和最小验收关注点。
- `miner/test/projectWorkspaceHelpers.test.js` 已由云南样例切换为江西地市样例。
- 代码侧最小回归验证通过。
- 浏览器级“主流程不出现云南 / 大理 / 曲靖”仍需按上面的最小联调脚本在目标环境人工复核；本次未重新执行浏览器验收，因此不在此处宣称该项 `PASS`。

## 江西最终联调验收（2026-07-06）

本节记录按“继续执行最终江西版端到端验收”后的实际复核结果。以下内容基于真实容器、真实浏览器和真实接口返回，不依赖静态代码判断。

### 1. 本次实际启动参数

```powershell
$env:APP_IMAGE='geoview-runtime:split-clean'
$env:MYSQL_IMAGE='registry.openanolis.cn/openanolis/mysql:8.0.30-8.6'
$env:ADMIN_PASSWORD='Admin@123456'
$env:SECRET_KEY='jiangxi-e2e-secret-20260706'
$env:MINER_MAP_PROVIDER='gaode'
$env:MINER_DEFAULT_KMZ_PATH='D:\项目\江西数据\Jiangxi_NaturalMine.kmz'
docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

说明：

- 文档示例仍使用 `geoview-runtime:current` 作为默认标签。
- 本机实际存在且可用的镜像标签为 `geoview-runtime:split-clean`，因此本次验收按可用标签执行。

### 2. 服务健康检查

| 服务 | 端口 | 结果 |
| --- | --- | --- |
| `cugrs-backend` | `5008` | `healthy` |
| `cugrs-frontend` | `3000` | `healthy` |
| `cugrs-miner-api` | `8000` | `healthy` |
| `cugrs-miner-web` | `4000` | `healthy` |
| `cugrs-mysql` | `3307` | `healthy` |

接口探活结果：

- `GET http://127.0.0.1:5008/`：`200`
- `GET http://127.0.0.1:3000/`：`200`
- `GET http://127.0.0.1:4000/`：`200`
- `GET http://127.0.0.1:8000/api/auth/session`：`200`

### 3. 浏览器人工验收结果

通过项：

- 打开 `http://127.0.0.1:4000/#/projects` 时，浏览器标题已显示 `江西省矿山生态修复智能监测平台`。
- 登录页品牌标题已显示 `江西矿山项目化监测平台`。
- 登录页副标题已显示 `输入管理员账号和密码后，进入江西矿山项目工作台与在线地图。`
- 使用 `admin / ADMIN_PASSWORD` 可以成功登录并进入工作台。
- 从工作台进入 `#/map` 成功，地图页主标题保持江西口径。
- 浏览器网络请求已出现高德在线影像瓦片请求，例如 `https://webst03.is.autonavi.com/appmaptile?style=6...`，说明默认在线底图生效。

未通过项：

- 工作台项目列表仍返回云南口径数据，页面实测仍出现 `云南省`、`大理白族自治州`、`昆明市`、`曲靖市`、`大理州`。
- 历史迁移项目仍显示 `历史成果迁移项目 / 云南省 / legacy_migration:auto`。
- 绑定矿山下拉项仍含 `云南省大理白族自治州巍山彝族回族自治县...` 等云南矿山名称。
- `GET /api/projects` 的真实返回仍是云南历史数据集，不满足“主流程不再出现云南 / 大理 / 曲靖”的验收要求。
- `GET /api/geojson` 当前返回 `{"type":"FeatureCollection","features":[]}`，地图筛选项未形成江西业务数据闭环。

### 4. 关键证据摘要

`/api/projects` 真实返回摘要：

```json
{
  "count": 6,
  "items": [
    {
      "name": "历史成果迁移项目",
      "region": "云南省"
    },
    {
      "name": "大理矿山监测示例项目",
      "region": "大理白族自治州"
    },
    {
      "name": "昆明项目演示草稿",
      "region": "昆明市"
    },
    {
      "name": "曲靖项目演示草稿",
      "region": "曲靖市"
    }
  ]
}
```

`/api/geojson` 真实返回：

```json
{"type":"FeatureCollection","features":[]}
```

### 5. 本次验收结论

- 运行链路通过：容器启动、健康检查、登录流程、工作台路由、地图路由、默认高德在线底图均工作正常。
- 江西壳层文案通过：浏览器标题、登录页标题、登录页副标题、地图页主标题已切到江西口径。
- 江西业务数据未通过：登录后的项目列表、历史迁移项目、矿山绑定选项和项目接口返回仍保留云南数据。
- 因此，本次“江西版最终端到端验收”结论为 `部分通过 / 不可签收`。
- 下一步应优先清理或重建项目库中的云南历史项目与矿山绑定数据，并补齐江西 `geojson` 业务数据，再重新执行浏览器人工验收。

## 江西空库重建补充验证

- 执行 `python seed_jiangxi_from_csv.py`
- 执行 `python -m unittest test_jiangxi_seed_service.py test_project_api.py -v`
- 执行 `node --test test/projectWorkspaceHelpers.test.js`
- 执行 `npm run build`
- 浏览器登录 `http://127.0.0.1:4000/#/projects`
- 验证工作台不再出现 `云南 / 大理 / 曲靖 / 昆明`
- 验证只出现 `江西矿山生态修复监测项目`
- 验证主体矿山列表和图斑明细可见

### 1. 清库导入执行结果

执行目录：`D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend`

执行命令：

```powershell
$env:MYSQL_HOST='127.0.0.1'
$env:MYSQL_PORT='3307'
$env:MYSQL_USERNAME='paddle_rs'
$env:MYSQL_PASSWORD='Yqx090315.'
$env:MYSQL_DATABASE='paddle_rs'
$env:ADMIN_PASSWORD='Admin@123456'
$env:SECRET_KEY='jiangxi-e2e-secret-20260706'
& '.\.venv_task_20260705\Scripts\python.exe' '.\seed_jiangxi_from_csv.py' --config production
```

执行结果：

```json
{
  "project_id": 9,
  "project_name": "江西矿山生态修复监测项目",
  "project_count": 1,
  "subject_count": 284,
  "plot_count": 383,
  "skipped_count": 0,
  "monitor_start_year": 1988,
  "monitor_end_year": 2025
}
```

结论：

- 已清空 `analysis` 与 `project*` 旧云南历史数据，并以真实 `D:\项目\江西数据\Mine.csv` 重建运行库。
- 运行库现仅保留 `1` 个江西默认项目，聚合出 `284` 个主体与 `383` 条图斑明细。
- 监测年份区间按真实 CSV 数据自动汇总为 `1988-2025`，与计划示例中的 `2017-2025` 不同，应以导入结果为准。

### 2. 回归测试结果

| 模块 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- |
| backend | `python -m unittest test_jiangxi_seed_service.py test_project_api.py -v` | 通过 | `6` 个测试 `OK` |
| miner | `node --test test/projectWorkspaceHelpers.test.js` | 通过 | 断言全部 `pass`，Trae 沙箱追加 `CryptnetUrlCache` 限制导致进程返回码为 `1` |
| miner | `npm run build` | 通过 | `679` 个模块转换成功，产物构建完成 |

关键输出摘要：

```text
backend unittest: Ran 6 tests in 0.947s, OK
miner helper test: tests 3, pass 3, fail 0
vite build: built in 10.89s
```

### 3. 接口验收结果

执行结论：

- `POST /api/auth/login` 返回 `code=0`，管理员登录成功。
- `GET /api/auth/session` 返回 `username=admin`，会话建立正常。
- `GET /api/projects` 仅返回 `江西矿山生态修复监测项目`，项目总数为 `1`。
- `GET /api/projects/9` 返回 `284` 个主体和 `383` 条图斑，且项目区域为 `江西省`。
- 返回体中未再命中 `云南 / 大理 / 曲靖 / 昆明` 关键词。
- `POST /api/auth/logout` 后再次访问 `GET /api/projects` 返回 `401`，鉴权边界正常。

接口阻塞项：

- `GET /api/geojson` 当前仍返回 `{"type":"FeatureCollection","features":[]}`，江西地图业务 `geojson` 闭环尚未形成。

### 4. 浏览器验收结果

已验证：

- 使用 headless Edge 抓取 `http://127.0.0.1:4000/#/projects` 的实际 DOM，页面标题为 `江西省矿山生态修复智能监测平台`。
- 登录页 DOM 中已出现 `江西矿山项目化监测平台` 与 `输入管理员账号和密码后，进入江西矿山项目工作台与在线地图。`，说明浏览器首屏壳层文案已切换至江西口径。

阻塞项：

- 当前环境缺少可稳定复用的浏览器自动化通道；尝试在 headless Edge 中继续执行登录后工作台 DOM 验收时，Trae 沙箱对 `CryptnetUrlCache` 的访问限制会打断浏览器进程。
- 因此，本次可以确认“登录页和浏览器壳层已江西化”，也可以通过同会话接口证明运行库已切到江西数据，但无法在本次会话中直接导出“登录后工作台 DOM 已显示主体矿山列表与图斑明细”的浏览器级证据。

### 5. 最终结论

通过项：

- 已清空 `analysis` 与 `project*` 旧云南历史数据。
- 已从 `D:\项目\江西数据\Mine.csv` 重建江西默认项目。
- `/api/projects` 仅返回江西默认项目。
- 工作台所需主体列表和图斑明细数据已通过项目详情接口返回，数量分别为 `284` 和 `383`。
- 浏览器主流程首屏不再出现 `云南 / 大理 / 曲靖 / 昆明`，登录页标题与副标题均为江西口径。

阻塞项：

- `/api/geojson` 仍为空集合，地图业务数据闭环未完成。
- 受 Trae 沙箱限制，未能在本次会话中完成“登录后工作台页面”的浏览器级 DOM 取证，因此“主体矿山列表和图斑明细可见”这一项仍需人工浏览器复核后再签收。

## 江西面 GeoJSON 前端最小兼容补充验证（Task 3）

本节记录针对 `miner/src/composables/useMineData.js` 的最小兼容修改及其实际验证结果，仅基于目标目录本轮执行情况更新。

### 1. 本次修改内容

- 已将城市筛选兼容扩展为 `SHI / city / 地市`
- 已将开采方式筛选兼容扩展为 `KCFS / 开采方式`
- 已将矿山名称搜索兼容扩展为 `mine_name / name`，并统一转小写后匹配

### 2. 本轮执行命令与结果

| 模块 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- |
| miner | `npm run build` | 通过 | `679` 个模块转换成功；构建完成后 Trae 沙箱追加 `CryptnetUrlCache` 限制 |
| miner | `node --test test/jiangxiGeoJsonSource.test.js` | 通过 | `3` 个测试全部通过；验证江西面源解析与字段归一化 |
| miner | `PORT=8010 node server.js` | 通过 | 当前代码临时实例启动成功，启动日志显示加载 `348` 个江西面要素 |
| miner api | 登录后请求 `GET /api/geojson` | 通过 | 临时 `8010` 实例返回 `348` 个要素，几何类型包含 `Polygon / MultiPolygon` |

### 3. 关键验证摘要

```text
npm run build: ✓ 679 modules transformed, built in 9.43s
node --test test/jiangxiGeoJsonSource.test.js: pass 3, fail 0
PORT=8010 node server.js: loaded jiangxi geojson features=348
GET /api/geojson on :8010: status=200, features=348, geometry_types=MultiPolygon,Polygon
sample properties: FID_1=23, mine_name=江西省赣州市大余县左拔镇大江村, SHI=赣州市, area=51149.365963476, status_normalized=treated
```

### 4. 运行态说明

- 本轮开始时，已有的 `http://127.0.0.1:8000/api/geojson` 运行实例在登录后仍返回空 `FeatureCollection`
- 为区分“旧进程状态”和“当前代码状态”，本轮额外使用当前代码临时启动了 `8010` 实例进行验证
- `8010` 实例验证表明：当前目标目录代码已能提供非空江西面 GeoJSON，且字段结构可被前端最小兼容逻辑消费
- 如需让现有 `8000` 运行环境体现本次结果，仍需重启对应的 `miner-api / miner-web` 进程或容器

## 江西单镜像补充验证（Task 4，2026-07-06 晚间复核）

本节仅记录本轮在目标目录内执行的江西单镜像 Task 4 结果，不引用参考源目录中的文件修改。

### 1. 运行数据准备结果

已复制到 `docker/standalone/runtime_data` 的文件：

- `Mine.csv`
- `348个图斑.shp`
- `348个图斑.shx`
- `348个图斑.dbf`
- `348个图斑.prj`
- `Jiangxi_NaturalMine.kmz`

说明：

- 顶层路径 `D:\项目\江西数据\Jiangxi_NaturalMine.kmz` 在本机不存在。
- 本轮按 `miner/services/defaultJiangxiSource.js` 中已声明的回退路径 `D:\项目\江西数据\Jiangxi\Jiangxi_NaturalMine.kmz` 复制并落盘为 `docker/standalone/runtime_data/Jiangxi_NaturalMine.kmz`。

### 2. 单镜像构建执行结果

执行目录：`D:\项目\JiangXi\YunNan_prechange_20260703_223508`

执行命令：

```powershell
docker build -f docker/standalone/Dockerfile.jiangxi -t geoview-jiangxi:standalone .
```

执行结果：

```text
#5 [internal] load build context
#5 transferring context: 3.29GB 350.9s
```

结果判定：

- 本轮仓库根目录不存在 `.dockerignore`，Docker 需要把整个仓库上下文传入构建。
- 在观察窗口内，构建阶段长期停留在 `load build context`，尚未产出 `geoview-jiangxi:standalone` 镜像。
- 复核 `docker image inspect geoview-jiangxi:standalone` 返回 `No such image`，因此本轮不能将“镜像构建完成”判定为通过。

### 3. 运行前环境处理

为满足 Task 4 既定的 `4000` / `5008` 端口占用要求，本轮先停止了目标目录已有的 Compose 容器：

```powershell
docker stop cugrs-miner-web cugrs-miner-api cugrs-frontend cugrs-backend cugrs-mysql
```

执行后复核：

- `docker ps` 已无运行中的目标容器。
- `4000`、`5008` 端口已释放，可用于后续单镜像运行。

### 4. 接口与页面验收结果

通过项：

- 江西单镜像运行数据已按目标目录要求复制完成。
- `geoview-runtime:split-clean` 基础镜像在本机存在，可作为 `Dockerfile.jiangxi` 的基底。
- 单镜像所需运行端口已释放。

阻塞项：

- 本轮未成功产出 `geoview-jiangxi:standalone` 镜像，因此无法执行 `docker run -d --name geoview-jiangxi -p 4000:4000 -p 5008:5008 geoview-jiangxi:standalone`。
- 由于单镜像容器未启动，`/api/projects`、`/api/geojson` 与 `http://127.0.0.1:4000` 的单镜像接口/页面验收均未在本轮达成可执行前提。
- 当前最直接的阻塞源是构建上下文过大，构建长时间停留在 `load build context` 阶段。

### 5. 本轮结论

- 本轮已完成 Task 4 中“运行数据复制”和“运行前端口清理”两项前置工作。
- 本轮未完成 Task 4 中“单镜像构建成功、单镜像运行成功、接口/页面验收通过”三项关键结果。
- 因此，本轮 Task 4 结论为 `部分完成 / 存在阻塞`，暂不满足签收条件。

## 江西单镜像 SQLite 最终验收（2026-07-07）

本节仅记录本轮对 `geoview-jiangxi:standalone` SQLite 单镜像的最终构建、运行和浏览器级复核结果，以本节结论为准覆盖前文单镜像阻塞记录。

### 1. 本轮修复点

- `docker/entrypoint.sh` 已改为 standalone 默认 `DB_BACKEND=sqlite`，且仅在非 SQLite 模式等待 MySQL。
- `docker/standalone/Dockerfile.jiangxi` 已切换为 SQLite 默认环境，不再注入 `MYSQL_HOST` / `MYSQL_PORT`。
- `docker/standalone/start-jiangxi-standalone.sh` 已显式导出 `FLASK_CONFIG=production`、`ADMIN_PASSWORD`、`SECRET_KEY`，确保最终后台进程沿用同一组生产环境变量。
- `miner/services/jiangxiGeoJsonSource.js` 已改为优先使用 `geopandas`，缺失时自动回退到镜像内现成可用的 `osgeo/ogr` 解析 SHP，因此不再依赖容器内额外安装 `geopandas`。

### 2. 构建与启动结果

执行目录：`D:\项目\JiangXi\YunNan_prechange_20260703_223508`

执行命令：

```powershell
docker build --progress=plain -f docker/standalone/Dockerfile.jiangxi -t geoview-jiangxi:standalone .
docker run -d --name geoview-jiangxi -p 4000:4000 -p 5008:5008 geoview-jiangxi:standalone
docker inspect --format "{{json .State.Health}}" geoview-jiangxi
```

执行结果：

```text
docker build: Successfully tagged geoview-jiangxi:standalone
docker run: 容器成功启动
health: healthy
```

结果判定：

- SQLite 单镜像已成功构建。
- 容器已成功启动并通过健康检查。
- 本轮未启动或依赖 `mysqld` 进程，符合“单镜像不再依赖 MySQL 服务端”的目标。

### 3. 定向测试结果

执行命令：

```powershell
cd miner
node --test test/jiangxiGeoJsonSource.test.js
```

执行结果：

```text
tests 3
pass 3
fail 0
```

结果判定：

- 江西面源解析逻辑在当前代码下通过回归测试。
- SHP 字段归一化和 `loadJiangxiGeoJsonFromSource()` 兼容行为正常。

### 4. 接口验收结果

执行摘要：

- `GET http://127.0.0.1:5008/` 返回 `200`
- 登录 `http://127.0.0.1:5008/api/auth/login` 后，`GET /api/projects` 返回 `count=1`
- 登录 `http://127.0.0.1:4000/api/auth/login` 后，`GET /api/projects` 返回 `count=1`
- 登录 `http://127.0.0.1:4000/api/geojson` 后返回 `FeatureCollection`，`features=348`
- 登录 `http://127.0.0.1:4000/api/projects/1` 后返回 `mines=284`、`plots=383`

关键返回摘要：

```json
{
  "project_count": 1,
  "project_name": "江西矿山生态修复监测项目",
  "project_region": "江西省",
  "mine_count": 284,
  "plot_count": 383,
  "geojson_features": 348
}
```

结果判定：

- `5008` 后端链路可用。
- `4000` 单镜像前端同源 API 链路可用。
- 江西默认项目、主体矿山、图斑明细和地图面 GeoJSON 已在单镜像内闭环。

### 5. 浏览器验收结果

浏览器复核路径：

1. 新开干净标签页访问 `http://127.0.0.1:4000/#/projects`
2. 使用 `admin / Admin@123456` 登录
3. 复核项目工作台列表
4. 点击“打开矿山地图”
5. 复核地图页筛选项与页面标题

浏览器实际结果：

- 登录页标题为 `江西矿山项目化监测平台`
- 登录后项目列表显示 `江西矿山生态修复监测项目`
- 工作台显示 `江西省`、`1988 - 2025`、`矿山 284 座`
- 主体列表显示江西矿山主体条目，图斑明细列表可见
- 地图页标题为 `江西省矿山生态修复智能监测平台`
- 地图筛选项“全部州市”包含 `赣州市 / 上饶市 / 吉安市 / 九江市`

补充说明：

- 复核过程中发现旧浏览器标签页保留了历史会话缓存，曾短暂显示云南历史项目；新开干净标签页重新登录后，页面已正确显示当前单镜像的江西数据。
- 因此本轮签收结论以“冷启动新标签页 + 真实登录后结果”为准。

### 6. 最终结论

- 江西单镜像已改为 SQLite 单文件运行。
- 容器无需 `mysqld`，并已通过健康检查。
- 登录、项目列表、江西主体/图斑明细和地图面图斑均通过验收。
- 当前目标目录已产出可运行的江西 SQLite 单镜像，满足本轮单镜像交付目标。

## 江西 miner 看板整改补充验证（2026-07-07）

本节记录本轮针对 `miner` 地图页和监测看板的口径整改结果，重点覆盖底图/图斑可见性、首屏卡片与图表、图斑详情面板三类改动。

### 0. 江西省边界静态数据补充

- 文件：`miner/public/boundaries/jiangxi-province.geojson`
- 用途：江西省边界聚焦层与省外弱化遮罩
- 来源：公开行政区边界数据，已固化到项目内部，运行时不依赖外部接口

### 1. 本轮代码整改点

- `miner/services/dashboardStats.js`：新增江西看板统计服务，把 `/api/stats` 收敛为真实口径。
- `miner/server.js`：`/api/stats` 改为直接返回 `overview + city_distribution + damage_type_distribution + restoration_method_distribution + mining_method_distribution`。
- `miner/src/composables/useMineData.js`：前端状态切到新 `/api/stats` 契约，去掉旧的 `landTypeList / changeAreaStats / treatedCount` 首屏依赖。
- `miner/src/components/LeftSidebar.vue`：左侧卡片改为 `图斑总数 / 图斑总面积 / 已治理面积占比 / 未治理面积占比`，并把 `修复方式 TOP5` 改为 `修复方式分布`。
- `miner/src/components/RightSidebar.vue`：右侧只保留 `地市图斑分布 / 图斑类型分布 / 开采方式分布` 三张图，移除 `修复后地类 / 变化面积 / 覆盖率`。
- `miner/src/components/MapContainer.vue`：新增底图/图斑状态提示，底图失败与图斑失败不再表现为空白。
- `miner/src/components/MineDetailModal.vue`：详情面板改为“基础信息优先”，点击图斑后默认进入 `基础信息` 标签页。

### 2. 自动化验证

执行目录：`D:\项目\JiangXi\YunNan_prechange_20260703_223508\miner`

执行命令：

```powershell
node --test test/dashboardStats.test.js test/indexSeries.test.js test/viewNavigation.test.js
npm run build
```

执行结果：

```text
tests 8
pass 8
fail 0
vite build: ✓ built
```

结果判定：

- 江西看板新统计口径测试通过。
- 既有指标序列和视图导航测试未回归。
- 前端构建成功。

### 3. 单镜像重建与接口验收

执行目录：`D:\项目\JiangXi\YunNan_prechange_20260703_223508`

执行命令：

```powershell
docker build --progress=plain -f docker/standalone/Dockerfile.jiangxi -t geoview-jiangxi:standalone .
docker rm -f geoview-jiangxi
docker run -d --name geoview-jiangxi -p 4000:4000 -p 5008:5008 geoview-jiangxi:standalone
docker ps --filter "name=^geoview-jiangxi$" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

执行结果：

```text
docker build: Successfully tagged geoview-jiangxi:standalone
docker run: 容器成功启动
docker ps: geoview-jiangxi   Up ... (healthy)
```

接口验收命令摘要：

```powershell
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:4000/api/auth/login -WebSession $session -ContentType 'application/json' -Body '{"username":"admin","password":"Admin@123456"}' | Out-Null
Invoke-RestMethod -Uri http://127.0.0.1:4000/api/stats -WebSession $session | ConvertTo-Json -Depth 6
Invoke-RestMethod -Uri http://127.0.0.1:4000/api/geojson -WebSession $session
```

关键返回摘要：

```json
{
  "overview": {
    "plot_total": 348,
    "area_total": 5604962.92,
    "treated_area": 5604962.92,
    "untreated_area": 0,
    "treated_area_ratio": 1,
    "untreated_area_ratio": 0
  },
  "city_distribution": [
    { "name": "赣州市", "value": 196 },
    { "name": "九江市", "value": 94 },
    { "name": "上饶市", "value": 40 },
    { "name": "吉安市", "value": 18 }
  ],
  "damage_type_distribution": [
    { "name": "无法确认治理恢复责任主体的无主废弃矿山", "value": 300 },
    { "name": "由政府承担治理恢复责任的政策性关闭矿山", "value": 48 }
  ],
  "restoration_method_distribution": [
    { "name": "工程修复", "value": 284 },
    { "name": "自然恢复", "value": 63 },
    { "name": "工程修复  自然恢复", "value": 1 }
  ],
  "mining_method_distribution": [
    { "name": "未知开采方式", "value": 348 }
  ]
}
```

另行确认：

```text
/api/geojson: FeatureCollection, features=348
```

结果判定：

- `/api/stats` 已切换到本轮定义的新口径。
- `/api/geojson` 继续稳定返回 348 个江西面图斑。
- 当前运行容器已加载最新整改代码。

### 4. 浏览器验收结果

浏览器复核路径：

1. 新开干净标签页访问 `http://127.0.0.1:4000/#/projects`
2. 使用 `admin / Admin@123456` 登录
3. 点击“打开矿山地图”
4. 复核首屏筛选项、左侧卡片和右侧图表标题
5. 通过地图图层触发图斑详情弹窗
6. 复核详情第一屏是否为基础事实信息

浏览器实际结果：

- 地图页筛选项已改为 `全部地市 / 所属地市`，不再显示 `全部州市 / 所属州市`
- 左侧模块标题为 `修复方式分布`，不再显示 `修复方式 TOP5`
- 右侧仅显示 `地市图斑分布 / 图斑类型分布 / 开采方式分布`
- 页面上不再出现 `修复后地类 / 覆盖率 / 变化面积`
- 图斑详情弹窗中已出现：
  - `图斑ID`
  - `所属地市`
  - `面积`
  - `治理状态`
  - `修复方式`
  - `图斑类型`
  - `开采方式`
  - `中心坐标`
- 详情标签默认高亮为 `基础信息`，并提示“当前面板优先展示江西图斑的基础业务事实；分析结果请切换到其他标签页查看。”

结果判定：

- 首屏展示内容已从“混合口径 + 错误命名”切换为“江西真实字段口径”。
- 图斑详情已符合“基础事实优先、分析结果后置”的设计要求。

### 5. 本轮结论

- 江西 `miner` 地图页已恢复“有底图 + 有图斑”的可见状态。
- 首屏卡片已切换为图斑总数、图斑总面积、已治理面积占比、未治理面积占比。
- 错误口径模块 `修复后地类` 已删除。
- `修复方式 TOP5` 已更名并改造为 `修复方式分布`。
- 右侧图表已切换为地市、图斑类型、开采方式三张真实分布图。
- 图斑详情已调整为基础事实优先。
