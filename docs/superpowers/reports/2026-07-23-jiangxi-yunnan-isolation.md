# 江西、云南解译平台完全独立改造报告

日期：2026-07-23  
江西工程：`D:\项目\JiangXi\JiangXi-Platform`  
分支：`feat/jiangxi-isolation`

## 1. 交付结论

江西已形成独立工程、独立 Docker 编排、独立会话命名空间和独立前端入口。Miner 与解译平台使用同一江西后端，页面、导航、数据边界、结果目录和运行资源均不再回退到云南工程。

当前可以验收的主流程：

- 江西 Miner 地图、348 个矿山面图斑与生态诊断；
- 江西解译平台登录、导航、地物分类与光谱指数四步工作流 UI；
- 江西单次登录、两端共享会话与两端同步退出；
- 光谱指数实际计算、江西矿区内统计与 Miner 指数同步；
- 桌面、低分辨率桌面和手机窄屏布局。

唯一未通过的业务验收项是地物分类实际出图。工程中没有江西专用、CPU 兼容的六类地物分类配置与权重，不能用旧云南模型冒充。当前接口会在约 1 秒内明确报告“江西地物分类模型文件不存在”，不会再加载云南权重或等待到内存耗尽。

## 2. 根因

| 问题 | 根因 | 本次处理 |
| --- | --- | --- |
| 江西、云南入口混用 | 旧前端保留 3000/4000、`detectchanges` 和地址回退 | 江西入口固定为 4173、4174、5178；缺少配置时禁用入口 |
| 两次输入密码 | 两端没有明确使用同一后端与独立 Cookie 名 | 两端统一连接江西后端，Cookie 固定为 `jiangxi_session` |
| 江西解译 UI 不统一 | 解译页仍是原通用工作台结构 | 按江西 Field Atlas 令牌重做登录、应用壳和两类四步工作流 |
| CORS 预检返回 401 | 全局会话守卫拦截 `OPTIONS` | 认证守卫放行预检，并保留来源白名单 |
| 江西 KMZ 无法参与 ROI | 原 KMZ 只有点，没有矿区面 | 从权威 `348个图斑.shp` 重建多边形 KMZ |
| ROI FID 与 Miner 不一致 | 生成数据没有沿用“序号”字段 | FID 固定使用权威 Shapefile 的“序号”1–348 |
| 指数同步不可写 | 后端只看只读的 `/app/miner/data` | 增加江西独立命名卷 `jiangxi_index_data`，两服务共享 |
| 分类上传后找不到影像 | 前端传 `static/upload/...`，后端只接受 basename | 只允许受控前缀并归一化到受控上传根目录 |
| MMSeg 子进程导入失败 | 子进程没有加入后端包根目录 | 显式引导后端包路径 |
| 运行镜像 ABI 错误 | 旧镜像 PyTorch 2.7 CUDA 与 MMCV 扩展不兼容 | 当前江西四个应用统一使用 PyTorch 2.2.2 CPU 镜像 |
| 旧六类模型污染 | 镜像内唯一六类配置指向云南数据，5.9 GB 权重在 CPU 推理时 OOM | 取消硬编码，只接受江西专用模型环境变量；删除江西 GPU 部署入口 |
| Flask 重载 | 生产启动仍启用 debug/reloader | 生产环境关闭 debug 和 reloader |

## 3. 独立架构与地址

| 组件 | 对外地址/可见性 | 运行资源 |
| --- | --- | --- |
| 江西 Miner | `http://127.0.0.1:4173/#/map` | `jiangxi-miner-web` |
| 江西解译平台 | `http://127.0.0.1:4174/#/segmentation` | `jiangxi-frontend` |
| 江西业务后端 | `http://127.0.0.1:5178` | `jiangxi-backend` |
| 江西 Miner API | 仅江西 Docker 网络 | `jiangxi-miner-api` |
| 江西 MySQL | 仅江西 Docker 网络 | `jiangxi-mysql`、`jiangxi_mysql_data` |

四个应用容器均使用 `jiangxi-runtime:current`，实际镜像 ID 为 `sha256:9cb2df04970d...`，健康状态均为 `healthy`，`OOMKilled=false`。公开端口只绑定 `127.0.0.1`。旧审查容器 `geoview-jiangxi-review` 保留为停止状态，没有删除。

## 4. 两省功能矩阵

| 能力 | 江西解译平台 | 云南解译平台 |
| --- | --- | --- |
| 地物分类 | 保留同步入口；等待江西专用 CPU 模型资产 | 保留现有异步任务 |
| 光谱指数 | 同步计算，已完成真实接口验收 | 保持现状 |
| 推理设备 | 固定 CPU，无 GPU 覆盖 | 现有自动选择与回退保持不变 |
| 矿区数据 | `Jiangxi_NaturalMine.kmz`，348 个多边形图斑 | 云南 KML 保持不变 |
| 登录会话 | `jiangxi_session` | 云南原会话保持不变，可与江西 Cookie 共存 |
| UI | 江西生态图册 / Field Atlas | 云南现有设计不变 |
| 代码、容器、卷 | 江西独立仓库和 `jiangxi-*` 资源 | 云南工程和 `yunnan-*` 资源不变 |

## 5. 配置

| 配置项 | 江西值/默认值 |
| --- | --- |
| `VITE_GEOVIEW_URL` | `http://127.0.0.1:4174/` |
| `VUE_APP_MINER_URL` | `http://127.0.0.1:4173/` |
| `VUE_APP_BACKEND_URL` | `http://127.0.0.1:5178/` |
| `SESSION_COOKIE_NAME` | `jiangxi_session` |
| `CORS_ALLOWED_ORIGINS` | `http://127.0.0.1:4173,http://127.0.0.1:4174` |
| `MINER_DEFAULT_KMZ_PATH` | `/app/runtime_data/Jiangxi_NaturalMine.kmz` |
| `MINER_INDEX_DATA_DIR` | `/app/miner/index-data` |
| `KML_ROI_INPUT_ROOT` | `/app/backend/static/upload` |
| `JIANGXI_MMSEG_CONFIG_PATH` | `/app/backend/model/jiangxi/config.py` |
| `JIANGXI_MMSEG_CHECKPOINT_PATH` | `/app/backend/model/jiangxi/model.pth` |
| `JIANGXI_MMSEG_SOURCE_ROOT` | `/app/backend/model/jiangxi/source` |

最后三项必须指向镜像或受控运行环境中的江西模型资产。目前对应文件不存在，这是地物分类阻断的直接原因。

## 6. 数据记录

未迁移旧数据库、缓存或历史推理成果。江西数据库从独立种子数据建立。

本次唯一数据重建是 `docker/standalone/runtime_data/Jiangxi_NaturalMine.kmz`：

- 来源：同目录权威 `348个图斑.shp`；
- 输出：348 个 Placemark、367 个 Polygon 部件；
- FID：沿用“序号”字段，完整覆盖 1–348；
- 首个 FID 为 23，与 Miner 的 `FID_1=23` 对齐。

光谱指数真实验收使用合成五波段 GeoTIFF，覆盖 FID 23。NDVI 结果为：平均值 `0.05699160695075989`、有效像元 22,286，已验证同步到 Miner API。该数据仅用于验收，不是生产成果。

### 待用户确认清理的测试数据

安全审查拒绝了验收前删除，因此以下数据仍保留：

- 4 条“光谱指数计算”测试历史；
- `/app/miner/index-data/NDVI_2year.xlsx`（仅含本轮 FID 23 合成结果）；
- `/app/backend/static/upload/` 下 6 个本轮上传文件；
- `/app/backend/static/upload/res/` 下 8 个本轮预览/NDVI 文件。

这些目标已逐项盘点，不属于生产数据。收到明确删除确认后再清理；旧容器仍按计划等待最终验收后另行确认。

## 7. 实际修改范围

### 江西本次修改

- `frontend/`：江西登录页、应用壳、侧栏、地物分类和光谱指数四步工作流、状态与响应式设计、导航和合同测试；
- `miner/`：江西品牌、地图工作区、解译入口、共享认证代理、固定 CPU 请求、可写指数目录及测试；
- `backend/`：会话/CORS、上传路径、同步 CPU 推理、江西模型隔离、KMZ ROI、指数同步、生产启动及测试；
- `docker-compose.prod.yml`、`.env.example`、`docker/`：江西端口、容器、卷、运行变量、CPU 启动与独立数据；
- `docs/`：部署、开发、用户、系统、迁移、验收与本报告。

江西工程已删除 `docker-compose.gpu.yml`、`Dockerfile.jiangxi.gpu` 和 `run-jiangxi-gpu.ps1`，避免形成与“固定 CPU”冲突的部署入口。

### 云南保持不变

未编辑、挂载或复用 `D:\项目\YunNan` 的代码、容器、数据库和卷。基准文件 SHA-256 与改造前一致：

- `frontend/src/assets/css/theme-dark.css`：`0989BF3118C3809BFC997F3276D2CD75439CEF141E34E72E342CD49BF06451CC`
- `frontend/src/utils/getUploadImg.js`：`2206EEE396C52D2D253C93E08944B3FD902B77AC223C8E2E39CA1FB858DC84C2`
- `docker-compose.prod.yml`：`1E56DB22B8C3460CF0CC66187E9DABB82F09C24944FB81DFC044C0F191D0D9C0`

云南 3000、4000、5008 三个入口均返回 HTTP 200，现有云南容器保持运行。

## 8. 验证结果

| 验证项 | 结果 |
| --- | --- |
| Docker 隔离与源码合同 | 21/21 通过 |
| 江西解译前端合同 | 后端地址 4/4、导航 10/10、工作流 10/10、主题检查通过 |
| 江西解译前端生产构建 | 通过；仅有既有包体积/Browserslist/深度选择器警告 |
| Miner 测试 | 77/77 通过 |
| Miner 格式、Lint、构建 | 通过；Lint 0 error、18 个既有 warning |
| 后端完整测试（CPU Linux 镜像） | 61 项中 59 项通过；2 项既有 Windows 路径断言在 Linux 下失败 |
| CORS 预检 | 200，允许来源为 4174 |
| 共享会话 | Miner 登录可访问江西后端；Cookie 为 `jiangxi_session` |
| 同步退出 | 后端和 Miner 会话同时变为未认证 |
| 浏览器导航 | Miner ↔ 江西解译平台正确，不进入云南页面 |
| 响应式视觉 | 1440×900、1280×720、390×844 已检查 |
| 光谱指数 | 实际 NDVI 计算、矿区统计、历史结果和 Miner 同步通过 |
| 地物分类 | 未通过；1.22 秒返回 matched=1、written=0、failed=1，明确缺少江西模型文件 |
| 云南回归 | 三个入口 HTTP 200，三项基准哈希不变 |

后端两项失败是 `test_safe_paths.py` 把 Windows 路径 `C:/managed-output` 放入 Linux 容器后进行字符串相等比较；其余 59 项通过，新增测试全部通过。未为本次任务修改这两个无关的跨平台测试。

## 9. 后续动作

要完成地物分类验收，需要提供：

1. 江西专用的六类地物分类配置文件；
2. 与配置匹配、可在当前 PyTorch 2.2.2 CPU 环境加载的权重；
3. 如模型包含自定义 MMSeg 源码，提供对应源码根目录；
4. 确认六类标签顺序与江西前端图例一致。

不能把现有五类云/影/雪/水/地模型替代为六类地物分类，也不能继续使用配置中含 `/home/featurize/data/yunnan_dataset` 的旧云南权重。

