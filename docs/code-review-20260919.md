# 第三轮全面代码审查报告（2026-09-19）

> **范围**：`f5110eb..HEAD`（24 提交，33 文件，+1747/−525）——大文件支持全链路（8GB 上传 / 整图流式拼接 / 未联动 U 命名空间 / nodata 剔除 / 超时放宽）+ miner 分类标签 + 前端上传改造；同时对 20260916 报告全部遗留项做回归对照，并按安全 spec（Flask/Express/Vue 三份）做全后端安全审计。
> **方法**：与上两轮一致（docs/code-review-20260914.md 前言）——4 个并行只读子代理（后端正确性 / 安全 / 前端 / miner）+ 地雷图 + 修复声明 vs 实现逐条对照 + 主控抽查验证 + 测试网实跑。本轮主控对全部 P0/P1 及两个子代理结论冲突点做了逐一实证（含证伪 1 条 HIGH）。
> **基线**：main `2841071`，工作树干净。审查期间只读操作，生产容器 `geoview-jiangxi-gpu-20260916` 未受影响。

---

## 结论速览

| 项 | 数量 | 摘要 |
|---|---|---|
| P0 | **1** | 光谱指数页历史删除入口整页消失（9a8944a 引入的前端回归，甲方必现） |
| P1 | **4** | 整图路径波段/归一化与联动路径不一致（结果错而不报错）；2841071 带红套件入库；无请求大小上限（非 TIFF 上传零限制）；整图同步长请求链路可用性弱（无轮询/断链误报/重试撞锁） |
| P2 | 27 | 后端 9 / 前端 8 / miner 9 / 安全 8 / 测试基建 3（有交叉），明细见第四节 |
| 20260916 遗留 | 17 项中 13 闭合 | P2-5 最小缓解接受、P2-6 残留一个面、P2-17 悬置决策项 |
| 测试网 | 192 / 107 / 34 | backend 192 中 **1 个真实失败**（P1-2）；miner 107 全绿；frontend 34 全绿 |

**未发现 P0 级安全漏洞。** 路径穿越、命令注入、SQL 注入、SSRF、认证覆盖、会话配置、文件名生成全部核实为干净（证据见第六节）。安全面上最需要在甲方检查前收口的是**请求大小上限缺失**与**两处绝对路径回显**。

---

## 一、测试网结果与运行车辆三陷阱（重要，先读）

本轮为后续所有测试跑法固化了权威命令，踩过三个环境陷阱，全部实测复现并归因：

1. **解释器陷阱**：GPU 镜像内有两套 Python——`/opt/venv`（**openpyxl 破损，缺 et_xmlfile**，任何 import 链带 openpyxl 即炸）和 `/opt/conda/envs/MMSeg310`（entrypoint 激活的真运行环境，依赖完好）。`docker exec <c> python` 或 `docker run --entrypoint python` 默认走前者，会得到大规模 import 错误的**假红**。生产 Flask（PID 实测）跑在 MMSeg310。
2. **STANDALONE_MODE 陷阱**：镜像 ENV 烘焙 `STANDALONE_MODE=1`，触发 `create_app` 的 SECRET_KEY 强制校验（`applications/__init__.py:34`），64 个测试秒挂。必须 `-e STANDALONE_MODE=` 覆盖为空。
3. **GPU 陷阱**：`kml_roi_inference_api` 在请求路径上急切解析设备（`resolve_inference_device`），GPU 镜像 + 不挂 `--gpus all` 时 5 个测试撞 `'CUDA 不可用'` 假红（这本身是测试基建缺陷，见 P2-T1）。

**权威跑法**（本轮实测通过，15.7s）：

```bash
MSYS_NO_PATHCONV=1 docker run --rm --gpus all \
  --entrypoint /opt/conda/envs/MMSeg310/bin/python \
  -e STANDALONE_MODE= \
  -v "D:/项目/JiangXi/JiangXi-Platform/backend:/app/backend" \
  -w /app/backend geoview-jiangxi:jiangxi-gpu-20260916-fixes \
  -m unittest discover -s . -p "test_*.py"
```

（Git Bash 下必须 `MSYS_NO_PATHCONV=1`，否则 `-w /app/backend` 被改写成本地路径。）

结果：**backend 192 tests → 1 failure（P1-2，真实）；miner `npm test` 107/107 绿；frontend `npm test` 34/34 绿**（含 9a8944a 后新增的 classificationAssets 4 例与契约测试 18 例）。

---

## 二、P0（甲方必现，验收前必修）

### P0-1 光谱指数页历史卡片「删除该组」按钮永不渲染——整页删除功能回归性丢失

- **位置**：`frontend/src/components/ImgShow.vue:26`（`v-if="item.record_id"`）；`frontend/src/views/mainfun/SpectralIndices.vue:428-440`（`deleteHistoryItem` 成死代码）；`backend/applications/schemas/analysis.py`（AnalysisSchema 无 `record_id` 字段，grep 零命中）；`frontend/src/utils/getUploadImg.js:42-49`（光谱页历史来自 `/api/history/list`，条目原样展开）。
- **证据**：9a8944a 为隐藏「未联动卡」的删除按钮给 ImgShow 加了 `v-if="item.record_id"`；但光谱指数页的历史条目**永远没有** `record_id`（后端该接口不产出此字段），`v-if` 恒假。f5110eb 上该按钮是无条件渲染的（range diff 可证）。
- **触发条件与影响**：甲方打开光谱指数页的任何历史记录 → 无删除入口、无任何提示。9a8944a 提交信息声称「3 P1 + 8 P2 全清」，实际打掉了另一页的既有功能。与 20260914 轮「miner 推理入口丢失」同级别的回归。
- **修复**：`v-if="item.record_id || (!item.unlinked && item.id)"`——kml_roi 历史走 `record_id`、光谱历史走 `id`、未联动卡（`record_id: null` 且 `unlinked: true`）仍隐藏。一行改动 + 契约测试各补一断言。
- **验证**：光谱页有历史 → 按钮出现 → 点击走 `/api/history/removeOne` 200；Segmentation 页未联动卡仍无按钮。

---

## 三、P1（现实条件下功能错误 / 验证门失守 / 安全硬伤）

### P1-1 整图推理路径的波段选择与归一化和联动切片路径不一致——uint16 / 4 波段影像「不报错但结果错」

- **位置**：`backend/applications/kml_roi/pipeline.py:120-131`（整图逐 tile 直接 `arr[:, :, :3]` 取波段 0-2，无 dtype 归一化，直接 `cv2.imwrite`）；对照联动路径 `backend/applications/kml_roi/raster_ops.py:147` → `read_tiff_as_rgb` → `tiff_processor.py`（4+ 波段取 B4/B3/B2 重排 + 非 uint8 做 2%-98% 百分位归一化）；模型 `backend/model/jiangxi/config.py:8-25` 为 0-255 定值 mean/std，无动态缩放。
- **触发条件与影响**：① uint16（遥感极常见）整图 tif：tile PNG 以 16-bit 写出，减 mean 除 std 后数值巨大，**预测完全不可信**；② 4 波段 tif：整图路径通道序与训练序相反，分类系统性错乱。f87731e 声称「任意 tif 整图推理」，实测只对 3 波段 uint8 成立。这类缺陷对甲方最危险——不报错、出图正常、**数值是错的**。
- **修复**：pipeline 逐 tile 处复用 `extract_rgb_from_multiband` + 非 uint8 归一化（512×512 开销可忽略），与联动路径共用同一函数（同时根治 P2-B1 的 2 波段崩溃）。
- **验证**：构造 uint16 / 4 波段 / 2 波段小 tif，断言整图路径与联动路径对同一图斑产出相同 tile PNG 字节（可直接落为单测，兼修 P2-B8）。

### P1-2 2841071 带红套件入库——强制验证门被跳过，超时行为变更未同步测试

- **位置**：`backend/test_kml_roi_subprocess_cleanup.py:96` 断言 `timeout == 3600`；`backend/applications/kml_roi/service.py:286-292` 已改为 `min(14400, max(3600, tiles*2*3))`。
- **证据**：本轮权威跑法实跑 192 tests → 恰好 1 个失败即此例（`AssertionError: 14400 != 3600`）。b7dfaf8（声称 192 全绿）在大文件支持 4 个提交**之前**；其后的 c16861d / dc43e6f / 32dfdc4 / **2841071** 均未再跑绿套件，2841071 把最后一个测试跑红了。
- **影响**：超时放宽本身是正确的验收修复，但①测试与实现不同步，下一个人跑套件会误判回归；②证明 AGENTS §5.1 强制验证门在验收期修复（直推 main）时被跳过——甲方若复跑测试网会看到红。
- **修复**：断言改为缩放公式（如 `self.assertEqual(calls[0]["kwargs"]["timeout"], min(14400, max(3600, tiles*2*3)))` 或对小图斑固定 3600 下限、对大 tile 数断言上限），随下一批修复一并提交。
- **验证**：权威跑法复跑 192 全绿。

### P1-3 无请求大小上限：8GB 限制只对扩展名 .tif 生效，其余上传零限制（安全/磁盘耗尽）

- **位置**：`backend/applications/api/file.py:26-36`（仅 `is_tiff_file` 命中才 seek/tell 比大小，且在 Werkzeug 已全量 spool 之后）；`backend/applications/configs/config.py` 全文无 `MAX_CONTENT_LENGTH`（grep 零命中）。
- **证据**：`.png` 在 `IMAGES_WITH_TIFF` 白名单内——已登录用户 POST 一个 9GB 的 `.png`：Werkzeug 无 `MAX_CONTENT_LENGTH` 会把整个 multipart spool 到容器临时目录，`photos.save` 再完整复制一份进 `static/upload` 卷，**上传成功落盘**。一次请求写 ~2× 文件大小（临时 + 落盘），几次即可写满 backend-static 卷或容器根盘，随后上传与整图推理（tile 落 /tmp）全部失败，构成持久 DoS；并发多个 8GB tif 同理。
- **修复**：`BaseConfig` 加 `MAX_CONTENT_LENGTH = int(8.5 * 1024**3)`（Werkzeug 超限直接 413 提前掐断，不落盘）；file.py 对非 TIFF 文件补同样的 seek/tell 上限。两行级改动。
- **验证**：`curl -F files=@8.6GB.tif` → 413；9GB png → 拒绝且磁盘无残留。

### P1-4 整图推理同步长请求链路可用性弱：无轮询、断链误报失败、重试撞锁

- **位置**：后端 `backend/applications/api/analysis.py:400-426`（同步等子进程，上限 4h）；前端 `frontend/src/api/upload.js:40-46`（单 POST）+ `frontend/src/utils/getUploadImg.js:157`（await 到响应）；全局 grep 无任何轮询。
- **触发条件与影响**：数千切片推理期间 HTTP 连接上无字节流动；跨 VPN / 反代 / 系统休眠断链后，前端 catch 走「Flash 推理失败，未生成任何结果」——**误报**（后端子进程实际还在跑并最终落盘）；用户按提示重试 → 撞跨进程锁 400「已有一个图斑推理任务正在执行」，且无法从 UI 确认在途任务状态。全屏 loading 也会锁 UI 数小时。
- **修复（最小）**：catch 分支区分网络错误，提示改为「连接已中断，任务可能仍在后端执行，请稍后刷新历史查看」；中期改提交 job + 轮询 `kml_roi_history`（后端已有历史列表可复用）。
- **验证**：推理中 kill 端口 → 提示含「仍在后端执行」；恢复后刷新能看到结果。

---

## 四、P2 明细

### 4.1 后端正确性（子代理 A，主控抽验 P1-1 时已复核关键代码）

| # | 标题 | 位置 | 要点 |
|---|---|---|---|
| B1 | 2 波段 tif 走整图路径 cv2 崩溃 | pipeline.py:123-126,130 | 只处理 `>3` 与 `==1`；2 通道 `cvtColor` 抛异常，子进程非零退出，用户看到无差别失败。联动路径可正常处理（灰度复制），行为不一致。与 P1-1 同一修复 |
| B2 | nodata 只看 o 期，n 期黑边不剔；`max<=2` 可能误剔深色水体【待验证】 | pipeline.py:117-128,175-192 | 两期覆盖不一致时 32dfdc4 想消灭的误判在 n 期复活；矿山深黑积水可能被整剔。修复：缓存 `row_raw_n` 联合剔除 + 连通边界条件 |
| B3 | 失败行未写入的 GTiff 块读出 0=草地而非 nodata=255【待验证】 | pipeline.py:84-100,195-201 | partial 结果中整行失败条带被 GIS 统计虚增草地。「GIS 可直接使用」承诺在 partial 场景失真。修复：`row_ok==0` 时写全 255 mask 行 |
| B4 | 非 worker 路径批超时固定 1200s 不随行宽缩放 | mmseg_inference_caller.py:303,352-357 | worker 路径已修 `3.0*len(names)`，子进程路径漏改；CPU + 宽影像一行超限即整行空白横带且无重试 |
| B5 | CPU 默认部署整图每行冷启动子进程，总时长或破 4h；超时后错误信息为空 | start-jiangxi-standalone.sh、mmseg_inference_caller.py:329-357、service.py:303-305 | 851MP≈59 行 × (init_model+整行推理)；`TimeoutExpired` 使 stdout/stderr 丢失，`err[:500]` 空。GPU 常驻 worker 无此问题。估算式 3s/片宜改环境变量可调 |
| B6 | 整图 U 产物 GB 级/次且无自动清理 | pipeline.py:97-100,235-244；cleanup_change_outputs.py:31；analysis.py:589-615 | 防误删方向正确，但缺运维出口。建议 cleanup 加 `--prune-unlinked N`（按 mtime 保留最近 N 个） |
| B7 | cleanup `--fid` 显式传 U 名无守卫，会按普通 fid 清掉整图产物 | cleanup_change_outputs.py:23-29；tiles.py:198-210 | 主循环有 `^U` 正则防护，`--fid` 分支漏了。运维按手册传 U 名 → 整图结果静默损坏 |
| B8 | 整图流式拼接（+325 行）零单元测试 | pipeline.py:14-291 | nodata/混淆矩阵/逐行写入/_src 拼接/partial 全靠手工回归；本轮 P1-1/P1-2 正是这类语义缝隙。用假推理器钉住：全 nodata、部分 nodata、失败行、超限四例 |
| B9 | 混合 KML（部分联动+部分未联动）推理成功但 runtime.kml 整体不合并 | service.py:165-173 | 全有全无是有意取舍，但联动部分白算+白写、结果不上图且原因不可感知。建议按 fid 过滤合并（merge_kml_increment 加 allow_fid 参数） |

### 4.2 前端（子代理 C）

| # | 标题 | 位置 | 要点 |
|---|---|---|---|
| F1 | b3c94f7「纯格式化」提交实际携带模板损坏修复；9a8944a「全清」提交实际打坏页面 | git show 两提交 | git 历史严重误导，revert/cherry-pick/bisect 会踩坑。不改代码，台账记录 + 补注说明 |
| F2 | 8GB 上传无前端大小预检、无进度、无取消 | getUploadImg.js:115-119；api/requestfile.js:7-48 | 选 9GB 要传完才被拒（`file.size` 现成没用）；8GB 全程只有文案无百分比；选错文件只能关页面。加预检 + `onUploadProgress` + AbortController |
| F3 | flash 卡 before_img 无「_src 缺失」回退，与后端历史列表回退不一致 | getUploadImg.js:246-247；analysis.py:539-541 | `_src` 拼接失败时闪卡左图 404，刷新后反而正常。`handleImageError` 里回填 afterUrl 即可 |
| F4 | 勾选预处理（CLAHE/锐化）把 fileList 整包重传，>500MB 注定失败 | preHandle.js:23-51；preprocess.py:48-54 | 8GB 放大后成为现实场景：2.4GB 白传一轮才吃 400。预检 >500MB 直接提示「大影像不支持预处理预览」 |
| F5 | 页面切换丢失 running 守卫，可同时发起第二组 8GB 上传 | Segmentation.vue:136-145；getUploadImg.js:82-85 | 守卫是实例字段，路由离开即失效。提升到模块级单例或 AbortController |
| F6 | 契约测试精确字面量锁 RunPanel 调用串（P2-10 式反向锁死残余） | analysisWorkflow.contract.test.mjs（「工作流保持江西同步链路」用例） | `seg\.upload\('地物分类','semantic_segmentation'\)` 未像同批其它断言一样引号无关化，prettier 一跑即红 |
| F7 | 非 flash 分支 URL 拼接无 String() 守卫、不去前导斜杠 | getUploadImg.js:47-48 vs :24-27 | 字段异常时出 `undefined` URL；跨代理多一跳 308。与 flash 分支同样写法 |
| F8 | 整图推理中断链的误报文案（并入 P1-4 修） | getUploadImg.js:157 catch | 见 P1-4 |

### 4.3 miner（子代理 D）

| # | 标题 | 位置 | 要点 |
|---|---|---|---|
| M1 | kml-roi 400 设备分支 `detail` 可回显完整命令行与绝对路径（P2-6 残留面） | server.js:1124-1133 | Python 子进程报设备错误时 `err.message` 为 `Command failed: <完整命令行>`，与上方注释自相矛盾。改固定文案或只透 stderr 尾部 |
| M2 | classification 路由 authGuard 双重挂载，每请求两次 Flask session 往返 | server.js:966 vs :1144 | `app.use` 已覆盖；路由级再挂一次疑为迎合字符串断言。删路由级，测试改断言 app.use |
| M3 | parseClassificationMatrixCsv 空单元格静默变 0，违背自身「畸形返回 null」契约 | classificationAssets.js:38 vs :16 | `Number('') === 0`；手工编辑/格式漂移的 CSV 显示假 0%。空串映射 NaN 让 isFinite 拦截 + 补用例 |
| M4 | `confusion_matrix.km2` 是死字段：上游从不产出该 CSV；map_fid 与旧端点类型不一致 | server.js:1192,1183 | 「三份 CSV」声明中 km2 永远 null。二选一：删字段或管线落盘；`map_fid: Number(fid)` 对齐 |
| M5 | 分类面板过期响应守卫只护成功分支，旧图斑的失败可覆盖新图斑数据 | EcologyDiagnosisPanels.vue:190-199 | catch 首行加同款 tbbh 守卫 |
| M6 | pair 与 +YYYY 产物混存时年份标签可能贴到另一轮推理的图上 | EcologyDiagnosisPanels.vue:207-218；server.js:1173-1178 | 服务端只返回一套口径：有 years 时忽略 pair |
| M7 | 「暂无地物分类推理结果」合法空态渲染成红色错误面板 | server.js:1164；EcologyDiagnosisPanels.vue:53-55,494-501 | 348 图斑大多数未跑过推理，打开即红字，验收观感差。404 区分为中性空态 |
| M8 | loadClassification 无 axios 超时，半开连接时 loading 永挂 | EcologyDiagnosisPanels.vue:187-189 | 加 `{ timeout: 15000 }` 与分级一致 |
| M9 | 遗留（非本区间引入）：400/500 分支回显服务器解析后绝对路径 | server.js:1003-1009 | `old_tif_path not found: <绝对路径>`、`Script not found: <绝对路径>`。只回显裸名/固定文案（与安全项合并处置） |

### 4.4 安全（子代理 B，经主控修正后定级）

> 子代理原本给出一条 HIGH「生产后端单线程 × 同步 4h 推理 = 一个请求冻结全后端」。**主控已证伪**：Flask 2.2.2 `app.run` 源码存在 `options.setdefault("threaded", True)`（app.py 未显式传 threaded），生产为多线程，4h 推理只占一个线程，healthcheck 不受影响。降级并入 P2-S1。此为「子代理结论必须主控复核」工作法的又一次实证。

| # | 标题 | 位置 | 要点 |
|---|---|---|---|
| S1 | 生产入口为 Werkzeug dev server + 4h 同步请求线程堆积 | docker/start-backend.sh:20（`exec python app.py`）；app.py:30-35 | threaded=True 下不再冻结全后端，但线程每连接新建无上限，重复提交整图推理 = 线程/内存堆积 + flock 外全 400；dev server 无进程管理/慢超时。中期：异步作业化（同 P1-4）或 gunicorn |
| S2 | Flask 2.2.2 / Werkzeug 2.2.3 已知 CVE 未修 | requirements.txt:1,20 | CVE-2023-46136（multipart 高 CPU DoS，未认证可打，与大上传面叠加）、CVE-2023-30861（缺 Vary: Cookie）。最小安全组合 `Flask==2.2.5 + Werkzeug==2.3.8`（2.2 系内升级），升级后 192 回归 |
| S3 | 上传白名单仅扩展名，无内容魔数校验；mime 取自客户端 | tiff_processor.py:48-50；init_upload.py:5-6；file.py:45 | 任意数据改名 .tif/.png 入库囤积（P1-3 修复后被上限兜住）。落盘后读 4 字节魔数 + rasterio 头探针 |
| S4 | 登录无速率限制与失败锁定 | auth.py:9-20 | 内网可达者可在线爆破唯一 admin。失败计数内存 dict（5 次锁 5 分钟）+ 固定延迟 |
| S5 | config.py MySQL 弱口令回退 "123456"（两处） | config.py:22,80 | compose 已强制注入，但代码层回退值是检查现成把柄。置空 + fail-fast（与 SECRET_KEY 同款） |
| S6 | interface 层 `os.path.exists(text)` 直通分支（API 层已收口，纵深缺口） | interface/analysis.py:99-100 | 当前不可达；删除该分支或收敛到 data_path 包含性检查 |
| S7 | SIGKILL 后 /tmp 残留 `kml-roi-infer-*`（单次可达数十 GB） | service.py:124,130 | 启动时清理 >1 天的残留目录 |
| S8 | `show_result` 分页 limit 未钳制 | analysis.py:226-234 | 复制 kml_roi_history 的 `max(1, min(100, limit))` |
| S9 | Windows 宿主无 fcntl 时推理锁完全失效（仅开发机直跑） | service.py:42-45；kml_roi_infer.py:39-42 | 容器内不受影响；可 msvcrt.locking 或进程内 Lock |

### 4.5 测试基建 / 车辆

| # | 标题 | 要点 |
|---|---|---|
| T1 | 5 个测试与运行环境 GPU 耦合（设备未 mock） | GPU 镜像不挂 GPU 即假红（本轮实测）；协作者在无 GPU 机器上验证 GPU 镜像会误判回归。设备解析在 API 测试层 mock 化 |
| T2 | 镜像内 `/opt/venv` openpyxl 破损（缺 et_xmlfile） | 非运行车辆，但任何 `docker exec python` / `--entrypoint python` 探针都会撞上假象（本轮首查即中招）。要么修复该 venv 依赖，要么文档钉死 MMSeg310 跑法 |
| T3 | 镜像 ENV 烘焙 STANDALONE_MODE=1 使套件默认不可跑 | 见第一节陷阱 2；测试车辆命令已在 AGENTS 补记候选 |

---

## 五、20260916 报告遗留项回归对照（17 项）

| 上轮编号 | 状态 | 证据 |
|---|---|---|
| P2-1 record_id 三段/两段分裂 | ✅ 已修 | 前端 2 段式（getUploadImg.js:250-252）；后端兼容 2/3 段（analysis.py:556-565）；契约测试双锁 |
| P2-2 KML 合并锁外执行+非原子写 | ✅ 已修 | 原子写 kml_merge.py:108-114；合并入持锁区 service.py:104,165-180；test_kml_roi_merge_lock 7 用例 |
| P2-3 Flask 侧子进程孤儿 | ✅ 已修 | service.py:196-230 Popen+killpg；测试钉心跳杀灭 |
| P2-4 cleanup 误删 _vN | ✅ 已修 | tiles.py:134-172 变体保留；test_kml_roi_cleanup_variants 4 用例 |
| P2-5 预处理进程内整图读内存 | ◐ 最小缓解（接受） | >500MB 且勾选增强/降噪时 400 拒绝（preprocess.py:44-54）；子进程化未做，注释自述 |
| P2-6 miner 错误回显 | ◐ 主项已修，残留两面 | 500 固定文案+测试在位；残留 M1（400 设备分支）与 M9（遗留路径回显） |
| P2-7 no_features 语义摊平 | ✅ 已修 | payload.message 透传（getUploadImg.js:193-195,282-288）+ 契约测试 |
| P2-8 download fetch 无 catch | ◐ catch 已修，超时未修 | download.js:34-41（9c1120e）；无 AbortController 超时，下载场景影响小 |
| P2-9 preHandle 双层静默 catch | ✅ 已修 | preHandle.js:43-50 明确 warning |
| P2-10 Login reason 迟到覆盖 | ✅ 已修 | Login.vue:69-88 watch immediate；authRedirect.js:19-33 query 合并 |
| P2-11 设备徽章硬编码 CPU | ✅ 已修 | 三页均绑 inferenceDevice；测试引号无关化（但 F6 残留一处） |
| P2-12 CRLF 测试位置+清单 | ✅ 已修 | TestCase 类 + rglob 全量收集（test_source_isolation.py:166-184） |
| P2-13 healthcheck 一致性守卫 | ✅ 已修 | test_source_isolation.py:129-137 |
| P2-14 miner 启动链子进程无超时 | ✅ 已修 | 15s/30s/120s 三级 + 测试全量锁定 |
| P2-15 15s fetch 无差别超时 | ✅ 已修 | SLOW_OP_TIMEOUT_MS=120s 恰好 3 处慢操作 + 测试 |
| P2-16 死链/孤儿测试三项 | ✅ 已收敛 | import:ndvi 移除+回潮测试；download 测试入 npm test glob；smoke 注释正名 |
| P2-17 GPU 链 mmcv 2.1.0 vs 2.2.0 护栏 | ⏸ 悬置（未动） | 属 GPU 链解押决策项，与上轮一致 |

---

## 六、核实为干净的方面（重点抽验，附证据）

**安全面（全后端 + miner + 前端）：**
- **路径穿越/U 命名空间全清**：`safe_paths.py:35-58` 标识正则 `U[1-9]\d*|[1-9]\d*` 全串匹配（`..`、绝对路径、盘符、分隔符全挡）+ `resolve()+relative_to` 双保险；`resolve_managed_file` 另有 basename 双重校验+后缀白名单；路由层第二道 `re.fullmatch`（analysis.py:459）；删除端点显式拒绝分隔符（:567）；`_iter_flash_records` 跳 symlink（:184,192）。主控对照过 resolve 链逐函数。
- **命令注入无**：应用代码 subprocess 仅 3 处，全列表参数、无 shell=True；`year/old_year/new_year` 经 `parse_year` 白名单（4 位数字、1800-2200）。
- **SSRF 修复无回归**：20260916 P1-4 的 static-server origin 收口与同源重组校验在位（docker/static-server.mjs:44-67,91-95）+ 回归测试在位；backend 无运行时出站 HTTP。
- **SQL 全参数化**：SQLAlchemy ORM，无字符串拼接 execute。
- **错误泄漏基本收口**：全局 handler 非 HTTP 异常只回通用文案；业务 ValueError 才回显。残留即 M1/M9/S4 中列出的结构化路径字段。
- **认证全覆盖、无新无认证端点**：六蓝图全部有门；SECRET_KEY standalone/production 强制；会话 HttpOnly+SameSite=Lax+12h；admin 口令 env 强制、空则启动失败。
- **上传落盘名服务端 uuid 生成**；上传目录不在静态根，仅经带鉴权 `/_uploads` 出网。
- **生产 debug 关闭**（config.yaml debug:false + FLASK_CONFIG=production）。

**大文件链路（子代理 A 逐条对照提交声明）：**
- 8GB 上限落地位置明确（file.py:27-36 + preprocess.py:22），dc43e6f 快速路径**未绕过**格式/尺寸闸门（跳过的只是切片预览与 500MB 预处理闸门，即设计目的本身）。
- 流式拼接属实非整图读内存：逐行画布常驻内存 851MP 下约 300MB 量级 + 40 亿像素防误用上限；重量全在子进程。
- merge lock 契约（7 用例）、孤儿杀灭、cleanup 变体保护（4 用例）、empty_cache 作用域修复无同类残留、bdb231b 逐批释放 CPU 路径守卫正确、_src 与 pred 拼接几何一致、U 命名空间六项联动落地且删除互不误伤、32dfdc4 nodata 边界语义正确（输入域问题除外）、2841071 超时公式实现与声明一致、05a31b4 失败不合并落地、f87731e 无 CRS 崩溃兜底成立。
- 前端：v-html/innerHTML/localStorage 零命中；:src 均服务端 URL + encodeURIComponent；record_id 2 段式前后端对齐；U 正则前后端一致；ImgShow 模板健康（v-for 稳定 key）。
- miner：classification 端点无穿越（fid 强制 `^\d+$` + 文件名硬编码 + year `^\d{4}$`）；percent_rownorm 口径三处一致；miner 107 测试真实有效。

---

## 七、修复优先级建议

1. **验收阻断（当天可清）**：P0-1 一行 v-if；P1-2 更新超时断言 → 套件回绿；P1-3 `MAX_CONTENT_LENGTH` + 非 tif 尺寸检查（两行级）；P1-1 整图路径复用 `extract_rgb_from_multiband`+归一化（兼修 B1）。
2. **安全小步（一个批次）**：S2 依赖升 `Flask==2.2.5/Werkzeug==2.3.8`（升后 192 回归）；M1/M9/S4 绝对路径与命令行回显三处收口；S4 登录限速；S5 MySQL 回退置空 fail-fast；S6/S8 两个小守卫。
3. **整图链路补强**：B2 n 期 nodata 联合剔除；B3 失败行写 255；B4 非 worker 超时缩放；B7 cleanup --fid U 守卫；B6 U 清理出口；B8 假推理器单测（钉住 P1-1/B2/B3 三处语义）；F2 前端预检+进度；P1-4 断链文案。
4. **体验与一致性**：F3-F7、M2/M3/M5/M6/M7/M8、B9、S7。
5. **决策项（偏产品/架构）**：整图异步作业化（job+轮询，根治 P1-4/S1）；dev server→gunicorn（若甲方查生产 WSGI）；混合 KML 按 fid 过滤合并；km2 字段二选一；GPU 链 mmcv 对齐（P2-17 沿旧）。
6. **测试基建**：T1 设备 mock 化；T2 修 /opt/venv 或钉死 MMSeg310 跑法；T3 随 AGENTS 补记权威命令。

修复时沿用并行子代理 + 文件所有权互斥 + 契约冻结 + 主控逐 diff 验收；验收期修复直推 main 的惯例**必须保留强制验证门**（P1-2 即反例）。

---

*方法与上两轮一致；本轮新经验：①「测试网红着入库」第一次被测试网本身当场抓获（2841071），验证门在验收期直推场景下最易失守；②子代理 HIGH 结论（threaded 单线程）被主控源码级证伪——并发/线程类断言必须查框架源码定默认值，不能凭直觉；③容器内测试的三车辆陷阱（解释器/ENV 烘焙/GPU 依赖）足以把「全绿」变成「64 红」，权威跑法必须连解释器路径一起写死。*

## 八、处置台账(2026-09-19 修复批,全部直推 main 且每 commit 过验证门)

| 发现 | 处置 | commit | 验证 |
|---|---|---|---|
| P0-1 光谱删除按钮消失 | 已修(v-if 分流) | 22ac848 | 契约先红后绿;38 绿 |
| P1-1 整图波段/归一化不一致 | 已修(同源函数+全局归一化参数) | 9395ef6 | 4 等价性单测 |
| P1-2 红套件入库 | 已修(断言对齐公式) | 5b1435b | 全量回绿 |
| P1-3 无请求大小上限 | 已修(MAX_CONTENT_LENGTH+非 tif 检查) | dcb2146 | 413/落盘用例 |
| P1-4 断链误报 | 最小修(区分文案);根治留 D1 | 083985f | 契约锁文案 |
| B1 2 波段 cvtColor 崩溃 | 已修(随 P1-1 同源) | 9395ef6 | 等价性单测 |
| B2 n 期 nodata 不剔除 | 已修(两期联合) | 2599a38 | 现状钉翻转 |
| B3 失败行读 0 | **证伪**:实测 255(nodata 生效) | 3097a59 | 回归钉 |
| B4 非 worker 超时固定 | 已修(_batch_timeout 共用) | ba682ac | 缩放双下限用例 |
| B5 冷启动/超时空错误 | 轻量修(stderr 尾部+env 可调);根治留 D1 | 4885baf | 2 用例 |
| B6 U 产物无清理出口 | 已修(--prune-unlinked N) | 6fc814a | 3 用例 |
| B7 --fid U 名无守卫 | 已修(^U 正则守卫) | 6fc814a | 2 用例 |
| B8 流式拼接零单测 | 已补(假推理器 5 例) | 3097a59 | 全绿 |
| B9 混合 KML 全有全无 | 悬置(产品口径,留 D3) | — | — |
| F1 git 历史误导 | 台账(AGENTS §7) | 167fa50 | — |
| F2 上传无预检/进度/取消 | 已修(file.size+onUploadProgress+Abort) | c0cbefd | 契约 3 能力 |
| F3 flash 左图 404 | 已修(回退结果图) | a4ab546 | 契约断言 |
| F4 预处理大影像白传 | 已修(>500MB 预检) | d049cfb | 契约断言 |
| F5 running 守卫实例级 | 已修(模块级单例) | d049cfb | 契约断言 |
| F6 契约字面量锁死 | 已修(字面量无关化) | 16764d6 | 39 绿 |
| F7 URL 拼接无守卫 | 已修(String+去斜杠) | 16764d6 | 39 绿 |
| F8 断链误报文案 | 并入 P1-4 | 083985f | 同上 |
| M1 400 设备分支回显命令行 | 已修(safeDeviceDetail) | 58eb4e4 | 源码锁 |
| M2 authGuard 双重挂载 | 已修(去路由级) | 0e609ee | 源码锁 |
| M3 CSV 空格变假 0 | 已修(NaN 拦截) | 0e609ee | 行为用例 |
| M4 km2 死字段 | 悬置(留 D4) | — | — |
| M5 catch 缺过期守卫 | 已修 | 0e609ee | 源码锁 |
| M6 years/pair 混存贴错标签 | 已修(服务端单口径) | 0e609ee | 源码锁 |
| M7 404 红错面板 | 已修(中性空态) | 0e609ee | 源码锁 |
| M8 无 axios 超时 | 已修(15s) | 0e609ee | 源码锁 |
| M9 遗留路径回显 | 已修(裸文件名) | 58eb4e4 | 源码锁 |
| S1 dev server 线程堆积 | 悬置(留 D2/D1) | — | — |
| S2 Flask/Werkzeug CVE | 已修(2.2.5/2.3.8) | ae93dad | 新旧双版本全量绿 |
| S3 上传无内容校验 | 已修(魔数前缀) | 4d4caa5 | 3 用例 |
| S4 登录无限爆破 | 已修(限速+固定延迟) | 99cfbbc | 5 用例 |
| S5 MySQL 弱口令回退 | 已修(置空+fail-fast) | 3eac18c | 源码锁+行为 |
| S6 interface 直通分支 | 已修(删除) | 19aea07 | 源码锁+行为 |
| S7 /tmp 残留数十 GB | 已修(启动清扫) | 3e82f47 | 2 用例 |
| S8 limit 未钳制 | 已修([1,100]) | 19aea07 | 2 用例 |
| S9 Windows 锁失效 | 接受(仅开发机直跑) | — | — |
| T1 GPU 耦合假红 | 已修(设备钉 cpu) | f4819fb | 有/无 GPU 双门 |
| T2 /opt/venv 陷阱 | 文档钉死(AGENTS §5) | 167fa50 | — |
| T3 STANDALONE_MODE 烘焙 | 文档钉死(AGENTS §5) | 167fa50 | — |
| 计划外:show data 恒 null | 已修(items_handle 补 return) | 19aea07 | 测试当场抓获 |

**测试基线变化**:backend 192 → 229(+37)/ miner 107 → 110(+3)/ frontend 34 → 39(+5),合计新增回归测试 45 个。生产容器未动;S2 依赖升级等生产生效随 D6 镜像重建。
