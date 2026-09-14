# 江西平台全面代码审查报告（2026-09-14）

审查基线：main `2ce326c`（工作树干净，与 origin/main 同步）。
方式：4 路并行模块审查（backend / 解译前端 / miner / docker 基础设施）+ git 健康度与验证门自查。
所有 P0/P1 级发现均经二次抽查确认（infra P1-1 经本机 Node 实测复现）。

**验证门状态（审查时全绿）**：miner `npm run verify` 90 单测全过 + vite build 成功；frontend `npm run build` 成功；backend 自镜像构建点 `d874d2b` 以来零代码漂移，2026-09-10 容器内 116 单测验收对当前 HEAD 仍有效。

---

## P0（用户可见功能已坏）

### P0-1 解译平台：四个预处理复选框（CLAHE/锐化/平滑/滤波）拆分后 refs 断线，功能全灭
- `frontend/src/utils/preHandle.js:6,15,53,61,96,109` 仍直接读 `this.$refs.clahe/sharpen/smooth/filter`，但这四个 input 的 ref 已随拆分迁入 `frontend/src/views/mainfun/segmentation/ParamsPanel.vue:45,57,78,88`。`this.$refs.clahe` 为 undefined，勾选即抛 TypeError，`uploadSrc.prehandle/denoise` 永不生效；RunPanel 的预处理预览区块（25-137 行）随之成为死 UI。
- 与 8346bd4（文件夹按钮）、2ce326c（删除该组）是同一模式，这是**第三处未修的同款断线**；冒烟测试恰好不覆盖这四个复选框。
- 连带发现：即使接好，主推理链路（`getUploadImg.js` 的 upload/kmlRoiInfer）也不消费 prehandle 参数——预处理对新链路整体是摆设。
- 修法：短期仿 `getCutCheckbox()` 加 `getParamCheckbox(name)` 桥接；正确做法是改受控绑定（v-model/:checked 到 seg.uploadSrc），删 DOM ref 读写，补冒烟用例。

### P0-2 miner：KML 推理与趋势统计两个弹窗入口在 UI 重设计中丢失，功能不可达
- `miner/src/components/MapDashboard.vue` 的 `showInferenceModal/showTrendReportModal` 全仓库只有置 false 与 :visible 绑定，**没有任何代码置 true**；TheHeader/LeftSidebar 均无入口按钮。`useMineData` 的 runKmlRoiInference/fetchTrendReport、后端 `/api/inference/kml-roi`、`/api/mines/trend-report`、`/api/kml/upload` 全部失去前端调用方。
- 发生在顶部栏统一（bb40910）前后的多轮 UI 重设计期间，无"有意下线"记录。
- 修法：在 TheHeader 或 LeftSidebar 恢复入口；或确认下线后整链删除。

## P1（安全 / 条件性崩溃 / 明确 bug）

### 后端
1. **SVG 上传构成同源存储型 XSS**：`backend/applications/extensions/flask_uploads.py:43` IMAGES 含 svg，`/api/file/upload` 放行 `.svg` 后经 `/_uploads/photos/` 以 `image/svg+xml` 内联返回，直接导航即在后端同源执行脚本、可携带凭据调用全部 API。修法：IMAGES 去 svg（前端不用 SVG 上传）或强制 attachment 下载。
2. **spectral 接口任意本地文件读取**：`backend/applications/api/analysis.py:224` 的 `kml_path` 与 `interface/analysis.py:76-107` 的 `raw_tiff_path` 均未过 safe_paths/受控根校验（对比 kml_roi 接口 `resolve_managed_file` 的严密实现）。可探测任意路径存在性并读取 KML/TIFF 统计信息。修法：与 kml_roi 对齐走受控根。
3. **推理失败详情永远显示 Unknown error**：`interface/mmseg_inference_caller.py:378` 读 `res.get('message')`，而生产者 `mmseg_segmentation.py:206/270` 写的键是 `"error"`。改成 `res.get('error') or res.get('message')`。
4. **SECRET_KEY 静默回退 'dev key' 且生产永不走 production 配置**：`configs/config.py:44`；容器 entrypoint 从不设 FLASK_CONFIG，强制校验仅在 production 分支生效。env 漏配时会话 cookie 可被伪造。修法：standalone 启动时强制显式 SECRET_KEY。

### 基础设施
5. **static-server 一条畸形 URL 即崩溃前端容器（已实证）**：`docker/static-server.mjs:65` 的 `decodeURIComponent` 对 `/%E0%A4%A` 等非法编码抛 URIError，无 try/catch，Node 默认退出进程；该脚本是 4173/4174 的主进程。修法：decode 失败返回 400 + 回归测试。
6. **miner 推理子进程无超时 + 单飞标志可永久锁死**：`miner/server.js:998-1005` execFile 无 timeout，Python 挂死则 `kmlInferenceActive` 永不复位，之后所有推理 409，只能重启。修法：加宽裕超时 + 超时 kill + 复位。

### 解译前端
7. **preHandle.js FormData 构造三重错误**（修好 P0-1 后立即暴露）：`preHandle.js:28,29` `append(...) || append(...)` 恒执行两次（把对象字符串化成 `[object Object]` 混入）；type 重复追加；ParamsPanel 传 `type=4` 而后端 `str_to_type("4")` 返回 None，入库必失败。建议预览链路按 upload() 口径重写或删除。
8. **裁剪上传产物恒为 undefined.png 且成果不可见**：`MyVueCropper.vue:201,210` 读从未赋值的 `this.file.name`；结果走老端点写老 Analysis 表，ResultsPanel 只读 flash 历史，成果永远不显示，且绕过年份校验。
9. **「恢复倾向等级」永远显示暂无**：`EcologyDiagnosisPanels.vue:140` 读 `recovery_tendency`，后端键是 `recovery_tendency_level`（`ecologySeries.js:55`）。

## P2（风险 / 技术债，精选）

**后端**
- 批量推理全量瓦片 float32 一次性驻留内存（`mmseg_segmentation.py:197-215`），348×2 期约 2GB，随图斑数线性增长；应分组流式加载。
- 单波段 GeoTIFF 在 `load_rs_image_with_gdal`（`mmseg_segmentation.py:94`）einsum 必抛 ValueError，报错误导。
- 用户自选 KML 同 fid 多 Placemark 静默丢图斑（`spatial_index.py:84-87`、`tiles.py:98`、`kml_merge.py:87-95` 三处叠加）。
- 生产用 Flask dev server + 同步 3600s 推理 + SQLite 无 WAL/timeout 调优（`configs/config.py:15-19`）；gunicorn 已在依赖却未用。
- `crop_prediction_by_polygon` ROI 边界画黄色（`raster_ops.py:257`），与 road 类颜色冲突——是全仓唯一漏改点（常量 `ROI_BOUNDARY_COLOR` 白色已定义）。
- 登录无速率限制；`init_db.py:66-71` 静默吞建表错误；index_sync 并发写共享 Excel 无锁且 fid 前导零丢失。

**基础设施**
- `entrypoint.sh:242-243` 最外层 `wait -n` 未就地兜底退出码，子服务非零退出时跳过 terminate()，与设计意图相悖（监督循环内 151-152 行已修，此处漏）。
- 健康检查时间预算从未整体核算：HEALTHCHECK timeout=15s vs 串行 4 次 HTTP(最坏 20s) + CPU 模式每 30s 全量 SHA-256 ~2GB（1.9GB pth + 1211 文件）；且无 `--start-period`，首启（种子导入+模型加载+vite 冷编译）可能直接判死。
- env 血统污染只根治了 MINER_LOCAL_TILE_URL 一个变量：`write-runtime-env.py:46-58` 对 VUE_APP_BACKEND_URL 等仍原样写入，含换行坏值可注入额外 env 行。
- GPU 构建期只 `import mmcv`，未验证 `from mmcv.ops import nms`（AGENTS §7 明确要求的验证门没落实到 Dockerfile）。
- compose 健康检查用 curl 而 standalone 用 Python urlopen，基础镜像若无 curl 则 compose 栈永久 unhealthy（需核实）。

**miner**
- 三个 auth 端点 async handler 无 try/catch（`server.js:57-67`），且容器未设 NODE_ENV=production，Flask 宕机时错误响应回显堆栈。
- 所有到 Flask 的 fetch 无超时（authBackend/projectBackend/geoviewBackend）；MapDashboard resize 监听器与 MapContainer Leaflet 实例在视图切换时泄漏（无 remove）。
- 瓦片 URL 模板 miner 消费侧无校验（只在写入侧根治），恶意 env 可把视野坐标外送任意外部 URL。
- InferenceModal 预填 `/app/backend/bianhua_2years/mine_TEST.tif` 与 `inferencePathPolicy.js:9-10` 只接受裸文件名矛盾，按默认值提交必 400。
- 死代码堆积：MineMap.vue（255 行零引用）、useMineData 约 110 行无调用逻辑、`kml_update` 契约残留、两段重复 CSV 解析；线性回归逻辑三处复制。

**解译前端**
- 会话心跳只挂在地物分类页，SpectralIndices 无心跳（长挂机后结果图 401，正是 AGENTS §7 记录的老问题）。
- `requestfile.js:34` 跨实例错关他人 loading；`download.js:33-49` 无 onerror，网络错误时全屏 loading 永不关闭。
- `URL.createObjectURL` 不 revoke（Segmentation.vue:267、download.js:16）。
- axios 0.26.1（CVE-2023-45857 区间）、element-plus 锁 2.1.10 均为 2022 年版本；多个死依赖；`Login.vue:52` 默认用户名硬编码 admin。
- GPU 部署时设备徽章/文案硬编码 CPU（Segmentation.vue:15、RunPanel.vue:8）。

## P3（归纳）

- 死代码清扫（前端 utils 约一半零引用：gettime/preview/loadMap/DraggableItem；后端 validate/upload/interface.utils 一批；docker init-mysql-runtime.sh 休眠）。
- 后端一批边界：history 列表 json.loads 无容错、path_global.md5_name 无扩展名 IndexError、analysis_type 白名单用 hasattr 可被模块属性穿透、manifest 映射每次请求全量重读。
- Dockerfile 层缓存顺序（先 COPY 源码再 npm ci）、镜像残留 /tmp 构建物与 dev 依赖、字体 MIME 缺失、瓦片断点续传按最大层级判断（破损层级永不自愈）。
- miner：CSV 导出无 BOM、`/tiles` 无认证（确认是否有意）、authGuard 无短 TTL 缓存、图表防溢出未覆盖 EcologyDiagnosisPanels。
- 前端：authRedirect 用 path 级跳转与 hash 路由参数错位（reason 丢失）；v-for index key 一批；`el-row type="flex"` 无效残留。

## 已检查未见问题的关键契约（值得肯定）

- 推理设备契约（仅 cpu/cuda:0、无静默回退）、worker 生命周期（SHA-256+类别合同+单次加载+串行复用、socket 丢失明确失败）、EPIPE per-connection 修复、批量推理原子性（批量失败退逐张、无部分输出）、并发推理临时目录隔离——全部符合 AGENTS.md 并有针对性回归测试。
- 六类顺序与调色板前后端逐项一致；TBBH 身份链、348 资产强校验、manifest 哈希绑定齐全。
- safe_paths 在 kml_roi 全链路覆盖完整；SQL 全 ORM 参数化；miner 路径校验体系（inferencePathPolicy/kmlUpload/localTileService）无逃逸通路；execFile 不走 shell。
- STANDALONE_MODE 强制 SQLite + 不覆盖前端 .env 双闸门齐备；无 secrets 烘焙进镜像；compose 端口全 127.0.0.1 且被 20 余条隔离测试锁死。

## 工程健康度（自查发现）

1. **`fix/jiangxi-platform-repair` 分支悬置**：84 提交未合入 main（基点 8 月初，git cherry 确认零 patch 等价），含 main 完全缺失的功能（首次改密流程、spectral service 276 行、MySQL 种子精度迁移修复），但与 9 月 main 重构冲突面大（backend 110 + miner 61 + frontend 21 文件）。悬置越久越难抢救，需决断：安排 cherry-pick 窗口抢救独立功能，或正式废弃。
2. **`feat/jiangxi-ui-brightness` 分支已被山地制图台重设计取代**（8 月初 5 提交），建议删除 worktree 与分支。
3. **`docs/readme-screenshots`（9-10，README 重写）在途待合并**；其第 67 行仍留「江西解译固定使用同步 CPU」旧句，与同文 GPU worker 描述矛盾，合并前应修。main 当前 README 同样过时。
4. **外层嵌套 `.git`（D:/项目/JiangXi/.git）仍在**，会误导仓库探测工具；此前已记录过，未清理。
5. 工作树干净、main 与 origin 同步、 miner 90 单测与两套前端 build 全绿——基线健康。

## 建议修复路线（按投入产出排序）

1. **半天窗口：安全与崩溃四件套**——IMAGES 去 svg、spectral 路径过受控根、static-server 400 兜底、SECRET_KEY 强制显式。全部低风险改动。
2. **半天窗口：两个功能复活**——预处理复选框受控化改造（顺手删/重写 preHandle 死链路）、miner 恢复推理与趋势统计入口。
3. **小步快修**：错误字段错配（error/message）、recovery_tendency_level 键名、execFile 超时、entrypoint wait -n 兜底、write-runtime-env 其余变量校验、HEALTHCHECK --start-period。
4. **排期项**：批量推理流式加载、gunicorn+任务句柄化、axios/element-plus 升级、分支决断（platform-repair 抢救或废弃）、死代码清扫。
