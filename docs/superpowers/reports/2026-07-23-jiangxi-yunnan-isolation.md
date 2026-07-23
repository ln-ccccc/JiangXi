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

地物分类模型已迁移到江西受控目录并完成实际出图。运行时使用只含 `state_dict` 的 CPU 推理 checkpoint，不携带训练优化器状态；配置、权重、元数据和定制源码均通过只读挂载接入 `jiangxi-backend`。使用用户上传影像完成命令行与 HTTP 接口双重验收，均匹配并写入 FID 22，失败瓦片为 0。

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
| 旧六类模型污染 | 归档六类配置指向云南训练目录，完整训练 checkpoint 携带优化器状态并在 CPU 推理时耗尽内存 | 迁移到江西受控目录，江西化有效配置，生成 1.97 GB 推理 checkpoint，并以哈希元数据绑定；删除江西 GPU 部署入口 |
| Flask 重载 | 生产启动仍启用 debug/reloader | 生产环境关闭 debug 和 reloader |

## 3. 独立架构与地址

| 组件 | 对外地址/可见性 | 运行资源 |
| --- | --- | --- |
| 江西 Miner | `http://127.0.0.1:4173/#/map` | `jiangxi-miner-web` |
| 江西解译平台 | `http://127.0.0.1:4174/#/segmentation` | `jiangxi-frontend` |
| 江西业务后端 | `http://127.0.0.1:5178` | `jiangxi-backend` |
| 江西 Miner API | 仅江西 Docker 网络 | `jiangxi-miner-api` |
| 江西 MySQL | 仅江西 Docker 网络 | `jiangxi-mysql`、`jiangxi_mysql_data` |

四个应用容器均使用 `jiangxi-runtime:current`，实际镜像 ID 为 `sha256:39d4bef8281652914c8e26db6187eaf445630d4a6ad647d19f18c7f68e6b70db`，健康状态均为 `healthy`。新镜像已内置江西模型并删除父镜像残留的旧 `mmseg_config`；四个运行容器均验证旧目录不存在。公开端口只绑定 `127.0.0.1`。旧审查容器 `geoview-jiangxi-review` 保留为停止状态，没有删除。

## 4. 两省功能矩阵

| 能力 | 江西解译平台 | 云南解译平台 |
| --- | --- | --- |
| 地物分类 | 保留同步入口；六类模型已迁移并通过 CPU 实际推理 | 保留现有异步任务 |
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
| `JIANGXI_MMSEG_MODEL_ROOT` | `/app/backend/model/jiangxi` |
| `JIANGXI_MMSEG_CONFIG_PATH` | `/app/backend/model/jiangxi/config.py` |
| `JIANGXI_MMSEG_CHECKPOINT_PATH` | `/app/backend/model/jiangxi/model.pth` |
| `JIANGXI_MMSEG_METADATA_PATH` | `/app/backend/model/jiangxi/metadata.json` |
| `JIANGXI_MMSEG_SOURCE_ROOT` | `/app/backend/model/jiangxi/dinov3_swinV1` |

模型资产路径必须位于受控江西模型根目录。元数据声明 `region=jiangxi`，六类顺序为 `grassland, forest, building, road, bareground, water`，并通过 SHA-256 绑定配置、权重与定制 Python 源码树。模型加载后还会校验实际 `dataset_meta.classes` 和分类头类别数。standalone 镜像内置江西资产；Compose 仅在江西后端叠加同目录只读挂载，云南工程不复用该目录。

## 6. 数据记录

未迁移旧数据库、缓存或历史推理成果。江西数据库从独立种子数据建立。

本次唯一数据重建是 `docker/standalone/runtime_data/Jiangxi_NaturalMine.kmz`：

- 来源：同目录权威 `348个图斑.shp`；
- 输出：348 个 Placemark、367 个 Polygon 部件；
- FID：沿用“序号”字段，完整覆盖 1–348；
- 首个 FID 为 23，与 Miner 的 `FID_1=23` 对齐。

光谱指数真实验收使用合成五波段 GeoTIFF，覆盖 FID 23。NDVI 结果为：平均值 `0.05699160695075989`、有效像元 22,286，已验证同步到 Miner API。该数据仅用于验收，不是生产成果。

### 模型迁移记录

- 来源：`D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend\model\mmseg_config` 只读归档；源训练 checkpoint SHA-256 为 `17985c633ec81a1b981421af8828b38c235994dfd1f3c61cf05649ce9b2044e3`。
- 目标：`backend/model/jiangxi`，运行时主权重 `model.pth` 为仅含 `meta + state_dict` 的推理 checkpoint，大小 1,970,599,978 字节，SHA-256 为 `419acab8cbf8934e7f5bc19eeb28c37f52bee93258de50c54e76babc5a369b97`。
- 配置：`config.py` SHA-256 为 `604c625d42f3e88f75af56bafe398b732e0fc177af8099ab50dd2eec148ee36b`；有效数据路径改为 `/app/runtime_data/jiangxi_dataset`，不再引用云南训练目录。
- 依赖：DINOv3 与 Swin 预训练权重的迁移前后 SHA-256 分别保持 `eadcf0ff...64f48` 和 `2f1a310c...06915`；运行时因完整参数已在主 checkpoint 中，关闭重复预训练初始化以降低内存峰值。
- 定制源码：迁移 MMSeg 与 DINOv3 必需源码；DINOv3 Hub 仅导出 backbone，避免加载本任务未使用且与 CPU PyTorch 不兼容的 CUDA 评估模块。1211 个 Python 文件的确定性树哈希为 `f98964d7b6e25ee9b0d095a4273b9172a9fec7583199de40afa04cb0b4f17f7f`，运行前强制校验。
- 等价审计：`backend/tools/migrate_jiangxi_checkpoint.py --verify-only` 已逐项核对源/目标 834 个状态项；834 项均为张量，键、形状、dtype 和张量值全部一致，源/目标文件哈希同时匹配。
- 边界：模型参数没有重新训练；源训练 checkpoint 的历史元数据曾记录云南训练目录。本次迁移只改变运行配置、部署边界和 checkpoint 包装，不声称完成江西样本再训练，江西精度仍需使用标注数据单独评估。

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
- `backend/`：会话/CORS、上传路径、同步 CPU 推理、江西模型隔离、模型资产与定制源码、checkpoint 迁移审计工具、KMZ ROI、指数同步、生产启动及测试；
- `docker-compose.prod.yml`、`.env.example`、`docker/`：江西端口、容器、卷、运行变量、CPU 启动与独立数据；
- `docs/`：部署、开发、用户、系统、迁移、验收与本报告。

江西工程已删除 `docker-compose.gpu.yml`、`Dockerfile.jiangxi.gpu` 和 `run-jiangxi-gpu.ps1`，避免形成与“固定 CPU”冲突的部署入口。

### 云南保持不变

未编辑、挂载或复用 `D:\项目\YunNan` 的代码、容器、数据库和卷。基准文件 SHA-256 与改造前一致：

- `frontend/src/assets/css/theme-dark.css`：`0989BF3118C3809BFC997F3276D2CD75439CEF141E34E72E342CD49BF06451CC`
- `frontend/src/utils/getUploadImg.js`：`2206EEE396C52D2D253C93E08944B3FD902B77AC223C8E2E39CA1FB858DC84C2`
- `docker-compose.prod.yml`：`1E56DB22B8C3460CF0CC66187E9DABB82F09C24944FB81DFC044C0F191D0D9C0`

云南 3000、4000 页面与 `5008/api/auth/session` 会话健康接口均返回 HTTP 200，现有云南容器保持运行且健康；5008 根路径按云南现有路由返回 404，不作为健康判定。

## 8. 验证结果

| 验证项 | 结果 |
| --- | --- |
| Docker 隔离与源码合同 | 29/29 通过 |
| 模型调用、固定 CPU 与 ROI 状态回归 | 16/16 通过 |
| 江西解译前端合同 | 后端地址 4/4、导航 10/10、工作流 10/10、主题检查通过 |
| 江西解译前端生产构建 | 通过；仅有既有包体积/Browserslist/深度选择器警告 |
| Miner 测试 | 77/77 通过 |
| Miner 格式、Lint、构建 | 通过；Lint 0 error、18 个既有 warning |
| 后端完整测试（CPU Linux 镜像） | 67 项中 65 项通过；2 项既有 Windows 路径断言在 Linux 下失败 |
| CORS 预检 | 200，允许来源为 4174 |
| 共享会话 | Miner 登录可访问江西后端；Cookie 为 `jiangxi_session` |
| 同步退出 | 后端和 Miner 会话同时变为未认证 |
| 浏览器导航 | Miner ↔ 江西解译平台正确，不进入云南页面 |
| 响应式视觉 | 1440×900、1280×720、390×844 已检查 |
| 光谱指数 | 实际 NDVI 计算、矿区统计、历史结果和 Miner 同步通过 |
| 地物分类 | 通过；用户上传 TIFF 匹配 FID 22；命令行 63.927 秒、切换新镜像前 HTTP 55.181 秒、切换后 HTTP 75.025 秒，均写入 1 个 FID、失败瓦片 0；HTTP 200、`success=true` |
| 云南回归 | 3000/4000 页面与 5008 会话健康接口 HTTP 200，四个应用容器 healthy，三项基准哈希不变 |

后端两项失败是 `test_safe_paths.py` 把 Windows 路径 `C:/managed-output` 放入 Linux 容器后进行字符串相等比较；其余 65 项通过，新增测试全部通过。未为本次任务修改这两个无关的跨平台测试。

## 9. 后续动作

地物分类运行链路已完成，后续只剩产品验收与模型质量评估：

1. 用户在 `http://127.0.0.1:4174/#/segmentation` 使用同一影像检查页面状态、Flash 结果卡和成果图；
2. 使用江西标注样本评估六类精度，确认归档模型是否满足江西业务标准；
3. 用户确认后再清理前述合成光谱测试数据和旧审查容器。

不得用五类云/影/雪/水/地模型替代本六类模型；如后续更换或重新训练权重，必须同步更新 `metadata.json` 中的类别顺序、区域和 SHA-256。
