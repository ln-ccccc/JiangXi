# 江西平台独立复审报告（2026-09-14 晚，针对 fix/code-review-20260914）

复审对象：`fix/code-review-20260914`（HEAD=b4d5c79，main=2ce326c 基线）。
方式：与当日早间评审（docs/code-review-20260914.md，未入库）独立的第二轮——5 路并行只读模块复审（后端安全 / 推理与数据管线 / miner / 解译前端 / docker 与仓库健康）+ 宿主机与容器内验证门实测。所有 P0/P1 级新发现均经二次人工抽查确认。

---

## 一、总体结论

1. **当日修复质量高**：旧报告 11 项 P0/P1 全部落地或基本落地，未见修复代码引入回归；两处仅"部分修复"（spectral 路径校验、裁剪成果可见性），详见下表。
2. **复审新发现 1 项 P0**：miner「上传 KML → 提交推理」链路必 400（上传接口返回绝对路径，提交端点只收裸文件名）——这正是旧 P0-2 恢复的那个推理入口的最后一段断链，两个单测各自通过但集成断链。
3. **安全残留 3 项 P1**：spectral 受控根校验两条绕过、`/static` 无鉴权旁路面、全局错误处理器（异常原文回显 + 全站失败恒 200，404 语义被吞——已在运行容器实测坐实）。
4. **验证门基本全绿**，唯一失败是镜像落后分支一个提交导致的已知契约断言失败（b4d5c79 已修，需重建镜像后复跑）。

## 二、验证门实测结果（本轮实际执行）

| 门 | 结果 |
|---|---|
| miner `npm run verify` | ✅ format+lint+93/93 单测+vite build 全过 |
| frontend 契约/冒烟/build | ✅ backend-url 4 + navigation 10 + workflow 13 全过；smoke PASS（含 CLAHE 受控勾选、删除接线）；vue build 成功（90.7s） |
| backend 容器内单测（AGENTS §5 权威跑法，容器 geoview-jiangxi-gpu-20260914 / 镜像 jiangxi-gpu-20260914-fixes） | ⚠️ 140 例 139 过 1 败：`test_standalone_healthcheck_allows_model_and_service_startup_time` 断言 `--timeout=15s` 与 Dockerfile 新值 `--timeout=30s --start-period=300s` 不符——镜像构建于 b4d5c79 之前，b4d5c79 正是修此断言。**分支尖端的该测试未经镜像验证**，重建后需复跑 |
| 运行容器探测 | 全部未知路由（/api/nonexistent、/no-such-page、/static/upload/res/）返回 **HTTP 200**（192 字节 JSON 错误体）→ P1-4 实测坐实；`/_uploads/photos/*` 无 Cookie 返回 401（登录门有效） |
| 镜像内容清点 | 镜像含 git 中不存在的陈旧代码（见 P2-14）；standalone 镜像**无 curl**（旧报告存疑项定案：compose 的 curl 健康检查在该基础镜像栈不可用） |

## 三、旧报告修复验证总表

| 旧编号 | 项目 | 判定 | 关键证据 |
|---|---|---|---|
| P0-1 | 预处理四复选框断线 | ✅ 彻底修复 | ParamsPanel.vue:47,58,78,88 状态绑定；preHandle.js 全文件无 $refs；getUploadImg.js:132-133 传参 → api/analysis.py:316-321 校验 → kml_roi/preprocess.py:22-99 真执行。旧结论“预处理对新链路是摆设”终结 |
| P0-2 | 推理/趋势入口丢失 | ✅ 入口与全链恢复 | TheHeader.vue:57-74 按钮 → MapDashboard → useMineData → BFF → 后端/脚本参数逐项匹配。⚠️ 同功能仍残留新 P0（见下） |
| P1-1 | SVG 上传 XSS | ✅ | flask_uploads.py:44 IMAGES 已剔 svg，上传强制 uuid 重命名+白名单 |
| P1-2 | spectral 任意文件读取 | ⚠️ 部分修复 | kml_path 与 dict 三键已收敛受控根；**字符串 list 项与 src/preview_src 键仍绕过**（见新 P1-2） |
| P1-3 | error 键错配 | ✅ | mmseg_inference_caller.py:378-381 `error or message`，生产者/消费者对齐，双向测试 |
| P1-4 | SECRET_KEY 静默回退 | ✅ | applications/__init__.py:33-34 production+standalone 双场景强校验；start-jiangxi-standalone.sh:55 require_env；compose:10 `:?` 必填 |
| P1-5 | static-server 畸形 URL 崩溃 | ✅ | static-server.mjs:67-74 try/catch 400 + 真实子进程回归测试（断言进程存活） |
| P1-6 | execFile 无超时+锁死 | ✅ | server.js:1024-1025 90 分钟超时+SIGTERM；finally 复位。孙进程缺口见新 P2-13 |
| P1-7 | preHandle FormData 三重错误 | ✅ | preHandle.js:24-28 单次 append、type 一次、传中文类型名 |
| P1-8 | 裁剪 undefined.png | ⚠️ 半修 | 文件名已修（Segmentation.vue:271-272 赋 file）；**成果仍写老 Analysis 表、本页只读 flash 历史永不可见**，提示语“可在下方查看”与事实相反（见新 P1-5） |
| P1-9 | recovery_tendency 键名 | ✅ | EcologyDiagnosisPanels.vue:140 ↔ ecologySeries.js:55；同面板全部键逐一核对无第二处错配 |
| P2 项 | 批量流式/entrypoint/env 校验/HEALTHCHECK/GPU mmcv 构建门/NODE_ENV/fetch 超时/心跳/泄漏清理 | ✅ | 批量推理驻留内存 2GB→约 24MB（weakref 测试锁定）；Dockerfile:139 start-period=300s+timeout=30s 且契约测试同步；Dockerfile:115 `from mmcv.ops import nms` 构建期验证；设备契约全读取点合规无静默回退 |

未修复的旧 P2/P3（现状维持）：同 fid 多 Placemark 三处、单波段 einsum、Flask dev server+同步长推理、登录无速率限制、hasattr 白名单穿透、md5_name IndexError、history json.loads 无容错、manifest 每请求重读、CSV 无 BOM、/tiles 无认证、axios 0.26.1 老依赖、死代码堆积。

## 四点、并行会话响应记录（2026-09-14 23:00–23:30 追加）

复审报告提交后，并行开发会话已在集成分支落地以下修复（提交 `9f3754f`、`16943a9`、`8643f2f`），本报告对应条目视为闭环或部分闭环：
- P1-1 /static 旁路：改用 `before_request` 对 `/static/` 统一鉴权（applications/__init__.py），并补 401 契约测试。
- P1-2 spectral 双绕过：API 层归一化扩展到字符串项与全部五个路径键（含 src/preview_src），interface 层 `_resolve_spectral_input` 增加第二道防线（含分隔符/编码一律收敛 basename）；主链路 `_normalize_uploaded_tiff_name` 支持三态归一并拒绝越界根。恶意路径 400 用例已补。
- P1-3 错误处理器：HTTPException 直通 + 通用文案 + 服务端日志，注册移入 create_app 工厂；健康探测端点改 /api/auth/session 适配 404 语义恢复。
- P0-1 KML 上传：`kmlUpload.js` 返回裸文件名（附 `kml_path_absolute`），测试同步；BFF 透传 `kml_update`/`inference_runtime` 键。
- P1-4 裁剪提示语：改为如实文案（不再宣称"可在下方查看"）。
- 上述项的本轮复核与剩余缺口由后续批次（fix/recheck-*）继续：A4 异常原文回显 31 处、A5 init_db 吞错、A6 分页/空 body 健壮性、B2 零结果提示、B3 502 文案、批次 C/D2/E/F 全部。

## 四、新发现问题（独立复审发现，旧报告未覆盖）

### P0（用户可见功能已坏）

**P0-1 miner「上传 KML → 提交推理」必 400**
`services/kmlUpload.js:24` 上传成功后返回 `kml_path = path.resolve(root, name)`（**绝对路径**，test/kmlUpload.test.js:17 还断言其绝对性）；`InferenceModal.vue:202-205` 把它原样写入表单；`server.js:980-985` 提交时过 `inferencePathPolicy.js:9`，绝对路径/含分隔符一律 `ManagedPathError` → 400「kml_path只能是受控目录内的文件名」。影响：推理弹窗的“选择并上传 KML”全流程走不通（上传成功、提交必败），除非用户手动改输入框为裸文件名。修法：上传响应改回裸文件名（或增加 `filename` 字段供提交用），同步修正该单测断言。

### P1（安全 / 明确 bug）

**P1-1 `/static` 路由无鉴权暴露上传与生成文件，`/_uploads` 登录门被同目录绕过**
`applications/configs/config.py:38` 上传目录 `static/upload`、`path_global.py:5-10` 生成目录 `static/upload/res/` 都落在 Flask 默认 static 目录内；蓝图级 `ensure_logged_in` 不覆盖 `/static/<path>`。免登录 GET `/static/upload/<uuid>.png` 可读取与 `/_uploads/photos/`（401 门实测有效）完全相同的文件。前置条件是知道文件名（uuid 不可枚举），但任何外泄 URL 即成免登录直链；前端零处引用 `/static/upload`，非有意公开面。修法：`Flask(..., static_folder=None)` 或将上传/生成目录移出 static。（机制链完整确认；探测时容器尚无运行期文件，实际读取未复现）

**P1-2 spectral 任意文件读取残留两条绕过**（旧 P1-2 的残部）
`api/analysis.py:112-113` 非 dict 项直接 `continue` 跳过归一化；`interface/analysis.py:84-86` 对 `candidate`（字符串项原值、或 dict 项的 `src/preview_src` 值）做 `os.path.exists` 直通 `rasterio.open`。登录用户可用 `{"list":["/任意/路径.tif"]}` 或 `{"src":"/任意/路径.tif"}` 读服务器任意 TIFF 统计、以报错差异探测任意路径存在性。新增测试只覆盖 dict 三键与 kml_path，无这两条用例。修法：底层 `_resolve_spectral_input` 收口为“basename 之外一律 resolve_managed_file”。

**P1-3 全局错误处理器：异常原文回显 + 全站失败恒 200 + 404 语义被吞（已实测）**
`backend/app.py:24-28` 把 `str(e)` 直接返回客户端（典型：rasterio 异常含绝对路径 api/analysis.py:308、子进程 stderr 前 500 字符 :374，共 12 处 `fail_api(str(exc))`）；`fail_api`（http.py:11-13）不带状态码恒 200；Exception 级 handler 按 Flask 2.2.2 MRO 吞掉 HTTPException → **abort(404)/未知路由全变 200**（运行容器实测确认）。`api/file.py:55` 还原样返回服务器绝对路径 `raw_tiff_path`。修法：handler 内 `isinstance(e, HTTPException): return e`；错误只回通用文案+日志 ID；`fail_api` 支持真实状态码。

**P1-4 裁剪上传成果仍不可见且提示语与事实相反**（旧 P1-8 残部）
`MyVueCropper.vue:210` 走老端点写老 Analysis 表，而本页历史只读 flash 目录扫描（kml_roi_history）；:212 提示“可在下方查看”永远不成立；裁剪链路仍绕过四位年份校验。修法：裁剪改走 kml_roi 链路或明确下线并改文案。

### P2（风险 / 技术债，按影响排序）

1. **GPU worker 服务端无读超时**：`mmseg_worker.py:249` 阻塞 recv 无 settimeout，哑连接/半开连接可无限期挂死单线程串行的 GPU 推理入口，监督循环只管进程退出管不住卡死。修：accepted socket 设超时。
2. **长推理必被标记 unhealthy**：推理期间 ping 在串行队列排队，`ping_worker` 客户端超时硬编码 2s（mmseg_worker.py:111），`--retries=5` → 推理持续 >150s（全量 348×2 必超）容器判 unhealthy。叠加 `interval==timeout=30s` 与 CPU 模式每 30s 全量 SHA-256 ~2GB（mmseg_inference_caller.py:135-162）的持续 IO。修：ping 超时环境变量化/心跳文件化，interval 拉开，哈希按 (size,mtime) 短路。
3. **推理并发无防护（前后端双侧）**：前端上传阶段走 requestfile.js 无 loading 锁（RunPanel.vue:14、getUploadImg.js:65-81 无 running 守卫）→ 可重复点击并发两组推理；后端 kml_roi 无并发锁且 `distribute_outputs` 写共享 `output_root/<fid>/`（tiles.py:120-158），同 fid 交错覆盖。两次并发同 fid 推理结果互相污染。
4. **同 fid 多 Placemark 静默丢图斑三处未修**（旧 P2 维持）：spatial_index.py:84-87、tiles.py:70-98、kml_merge.py:69-91；用户上传增量 KML 产生同 fid 时每次推理静默丢图斑。
5. **kml_update 键 BFF 链缺失（复审后修正，影响降级）**：BFF 响应不含 `kml_update`（server.js:1085-1101），execFile 链后端也不产出（KML 增量合并只存在于 Flask service 层）→ MapDashboard 的 kmlChangedCount 恒 0、"纯 KML 更新型推理关弹窗"分支死亡。~~runtime 键错配、writtenCount 恒 0~~ **修正**：`kml_roi_infer.py:113,117` 已在 stdout 层把 `inference_runtime` 改名为 `runtime`，BFF `server.js:1095` 读取正确；`writtenCount`（written_tbbh_list）贯通。实际残余影响仅为：推理零写入（无匹配图斑）时弹窗不关、无任何提示。
6. **spectral_live 端点从未存在**：`geoviewBackend.js:8` 请求 `/api/analysis/spectral_live/<fid>`，git 历史确认从未有过该路由 → miner 光谱 live 叠加永远静默 404 被吞（useMineData.js:186-237）。属“端点级 recovery_tendency 式静默”。修：补端点或删 overlay 链。
7. **index_sync Excel 并发写无锁**（index_sync.py:62-109）：并发光谱请求 lost update / Windows PermissionError 降级为 warning 丢数据。
8. **推理超时 kill 不覆盖孙进程**：SIGTERM 只发 kml_roi_infer.py 直接子进程（server.js:1017-1027），mmseg_inference_caller.py:321 再起的孙进程孤儿化继续占 GPU，且锁已复位可再并发。
9. **镜像含非 git 陈旧代码（血统污染）**：运行镜像 `/app/backend/run_inference_worker.py` + `applications/inference/`（7 月中旬代码，git 全历史不存在）+ `docker/start-inference-worker.sh`（引用构建时已删除的 model/mmseg_config 目录）——从旧基础镜像层继承，无启动路径引用，属死重量+误用陷阱+不可复现。修：Dockerfile 构建层 `rm -rf` 明确清理或换干净基础镜像。
10. **Docker 镜像工程债**：COPY 源码先于 npm ci（层缓存全失效）；npm cache 与 /tmp 暂存物烘进镜像（虚胖约 100-200MB）；.dockerignore 缺 `.worktrees/`（7 个工作树约 180MB 进构建上下文）、recovery-snapshots、docker/**/__pycache__。
11. **compose 与 standalone 健康检查语义漂移**：compose 仅 curl 根路径、无 start-period、无资产校验（docker-compose.prod.yml:81,102,130,153），且 standalone 镜像无 curl（实测）；MySQL 断连/资产损坏时 compose 栈仍 healthy。
12. **init_db.py 静默吞建表错误**（旧 P1 级未修）：common/scripts/init_db.py:69-76 回滚无日志无重抛，:90 无条件报成功。
13. **fetchEcologyProfile 无竞态防护**（useMineData.js:273-293）：快速连点图斑 A→B 时 A 迟到响应覆盖 B 的面板。

### P3（归纳，择要）

- 前端：会话过期 reason 全程丢失（authRedirect.js:4 hash 路由错位，用户看不到“登录已过期”）；`$refs.upload` 死引用（getUploadImg.js:121,231）；光谱页徽章硬编码 CPU 与 GPU 部署矛盾（SpectralIndices.vue:15 且被契约测试锁死）；downloadimgWithWords 无 catch；uploadSrc 深度 watch 自赋值 no-op；smoke 注释指向不存在的 upload-contract.test.mjs。
- 后端：history_delete 空 body TypeError；int(page) 无容错；worker 模式整批 1200s 超时余量约 2 倍（超时报失败但结果已落盘的状态不一致）；六类顺序三处独立字面量无一致性测试、docstring 颜色描述与 PALETTE 不符；kml_roi 与 upload 预处理-缩放顺序口径差异（CLAHE/中值核尺度相关，同参数效果不同）；worker 空 names 返回类型不符（不可达）。
- miner：authGuard 及 projects/geoview 路由 502 分支仍回显 error.message（13 处）；/api/health/jiangxi 无认证暴露 manifest 哈希/设备形态；stderr_tail 回传可能带内部路径；reviewMinerFixes.test.js 未纳入 format/lint 清单且接线断言是源码正则而非行为测试（P0-1 正是从这种测试的盲区漏出）；InferenceModal label 仍写“服务器路径”；uploads/kml 与 bianhua_2years 均非卷、重建即丢。
- 基础设施：py3.10 语法回归无守卫（test_write_runtime_env 在宿主 3.12+ 跑，坏代码回潮时仍绿——加一行 ast.parse feature_version 即可）；write-runtime-env 回退默认值零日志；static-server 代理分支 URL 构造在 try 外；compose mysql 健康检查 root 密码内嵌 command。
- 仓库卫生：fix/jiangxi-platform-repair 84 提交悬置满月（含 main 缺失的首次改密流程、spectral service 276 行）需决断抢救/废弃；feat/jiangxi-ui-brightness、docs/softcopyright-user-manual 建议删；docs/readme-screenshots 在途且含“固定同步 CPU”旧句；AGENTS.md §4 记录的验收镜像在合并本分支后即漂移（需重建验收）；驱动本轮修复的 docs/code-review-20260914.md 本身仍未入库。

## 五、无法确认项（需真机/决策）

1. 分支尖端（含 b4d5c79）的容器内后端测试——另一会话正在重建镜像，重建后按 AGENTS §5 复跑。
2. `/static` 免登录实际读取文件——探测时容器尚无运行期文件（重建后跑一次推理再验证）。
3. GPU 长推理实测（显存/时延/全量双跑，AGENTS §5.1 三级递进）本分支无记录。
4. spectral_live、光谱页 CPU 徽章是否属“本期明确不做”，需产品决策。
5. MINER_CHANGE_OUTPUT_ROOT 两链不同（compose 命名卷 vs standalone runtime_data）是否有意。

## 六、建议修复排序（供负责人决策）

1. **立即（小改动）**：P0-1 KML 上传返回裸文件名；P1-3 错误处理器（HTTPException 直通 + 停止回显原文/绝对路径）；P1-2 spectral 底层收口 + 补两条绕过用例；P1-1 static_folder=None。
2. **短期**：worker 读超时 + ping 超时环境变量化；推理 running 守卫（前端）+ fid 级写锁（后端）；kml_update/runtime 键对齐；孙进程按进程组 kill。
3. **合并 main 前**：重建镜像复跑后端 140 例；清理镜像陈旧代码；AGENTS §4 补记；评审报告与本报告入库。
4. **排期**：裁剪链路二选一（接通或下线）；spectral_live 二选一；同 fid 三处；Dockerfile 分层/缓存/ignore；分支决断（platform-repair）。
