# 全面代码审查报告（2026-09-16）

- **审查对象**：分支 `fix/code-review-20260914` @ c852490（与 origin 同步，待建 PR 合 main）。
- **审查基线**：`git diff 2ce326c..HEAD`（上次审查以来的 41 个修复提交，95 文件 +5449/-470），外加全项目全新扫描。
- **方法**：沿用 2026-09-14 既定工作法——4 路并行独立子代理（backend / 解译前端 / miner BFF / docker 基础设施），注入 AGENTS.md 契约与历史地雷图，跨层 grep 对照 + git 考古；每条 P1 由主控亲自复核后才采信（本文所有 P1 均标注复核证据）。
- **排除项（已定论，不再列为发现）**：axios 0.26.1 / element-plus 版本 CVE（离线内部部署，用户 2026-09-16 定论）；platform-repair 分支 84 提交悬置；裁剪链路接通或下线；AGENTS.md §4.1/§4.2 已记录并接受的镜像血统现状。

## 总体结论

**0 个 P0，4 个 P1，约 15 个 P2（去重后）。** 上次审查的 2 个 P0 修复（预处理复选框受控化、miner 推理/趋势弹窗入口恢复）经端到端贯通验证**真实有效**；绝大多数修复有对应测试且断言的是修复行为本身。本轮 4 个 P1 全部属于「修复批次自身的残留或盲区」：两处是上一轮修复声明覆盖不全（错误收口漏掉 project.py 8 个端点、畸形 URL 收口漏掉代理分支），一处是修复声明与实现不符（kml_update 透传为死键），一处是守卫机制本身失效（py3.10 语法守卫假绿）。**没有发现修复引入的运行时回归**，当前分支可以进入 PR 流程，P1 建议随 PR 或紧随其后的小批次修掉。

---

## P1（主控已逐条亲验）

### P1-1 泛化异常收口漏改：project.py 8 个端点吞掉业务校验消息，行内注释与事实相反

- **证据**：`backend/applications/api/project.py:39-46`（create）、`:51-58`（detail）、`:63-70`（update）、`:103-110`（timeline）、`:115-122`（archive）、`:127-134`（restore）、`:153-160`（export list）、`:179-186`（backup list）。8 个 handler 只有 `except Exception` 兜底，注释却写着「业务校验消息走上面的 ValueError 分支保持原样」——上面**没有** ValueError 分支。
- **生产者侧**（主控已核）：`backend/applications/project_hub/service.py:149`（"项目名称不能为空"）、`:152`（"项目状态不合法"）、`:120-123`（`_get_project_or_404` "项目不存在: X"，被 detail/update/timeline/archive/restore/export list/backup list 共用）。
- **触发路径**：a188139 泛化异常不回显改造时，POST `/api/projects` 传空项目名这类最普通校验失败，用户看到的是「项目操作失败，请稍后重试或联系管理员」。同批 analysis.py 改造正确保留了 `except ValueError`（`analysis.py:263-265`），证明是漏改而非设计。
- **修复**：8 处补 `except ValueError as exc: return fail_api(str(exc)), 400`，并修正失实注释。
- **漏网原因**：`test_project_api.py` 未覆盖校验失败消息路径（见验证门评估）。

### P1-2 kml_update 透传是死键：BFF 链路恒为 null，9f3754f 声明的功能不可达

- **证据**（主控已核两侧）：`miner/server.js:1097` 读 `parsed?.kml_update || null`；但 BFF execFile 的 `backend/kml_roi_infer.py` 输出的 summary 由 `pipeline.py:108-118` 生成，键集合为 status/total_features/matched_fids/output_root/failed_tiles/tile_errors/inference_runtime/**dist——**不含 kml_update**；`kml_roi_infer.py:150-196` 只把 inference_runtime 改名 runtime，全程无 kml_update。kml_update 只在 Flask 链路（`service.py:68-74,123` 的 merge_kml_increment）产生，而 miner 从不经过该链路。
- **触发路径**：经 miner 上传 KML → 推理 → 解析 stdout → `kml_update` 恒 null → `MapDashboard.vue:305-313` 的 `kmlChangedCount > 0` 自动关弹窗分支与 `InferenceModal.vue:150-154` 的"KML 已更新矿山信息"成功文案**永久不可达**。同因：BFF 链路根本不把上传 KML 合入默认 KML，"上传新增矿山"在该链路无持久化效果。
- **附带**：`server.js:1093-1094` 的注释「后端键为 inference_runtime」也不准确——`kml_roi_infer.py:150` 实际 pop 后改名 `runtime` 输出，miner 靠 `|| parsed?.runtime` 兜底才工作。
- **修复（二选一）**：a) BFF 链路真正落地——kml_roi_infer.py 增加 KML 合并并在 summary 输出 kml_update；b) 删除死透传与前端死分支，注释改为与 kml_roi_infer.py 实际输出一致。`miner/test/` 目前对 kml_update 零断言（死键写不出有效测试，恰是佐证）。

### P1-3 py3.10 语法守卫假绿：feature_version 在 3.12+ 宿主上拦不住 PEP 701 f-string

- **证据**（主控在本机 Python 3.14.4 实测复现）：`ast.parse("v = f'{os.environ.get('X', '')}'", feature_version=(3, 10))` → **ACCEPTED**；真 3.10 下是 SyntaxError。PEP 701（3.12）改变了 f-string 的 token 化方式，`feature_version` 不回退该文法。守卫位于 `docker/tests/test_write_runtime_env.py:46-51`，其注释「feature_version 让高版本宿主解释器也拒绝该回归」**与事实相反**。
- **触发路径**：未来任何人往 write-runtime-env.py 写回嵌套同类引号 f-string（正是 T22/23ac71a 那个 P0 的形态）→ 宿主测试全绿 → 容器 entrypoint SyntaxError 整机起不来。守卫复刻了它要堵的盲区。
- **修复**：守卫改为子进程调用真实 3.10 解释器（本机有 `py -3.10`，缺解释器时显式 skip 并告警），或对 f-string 段做定向词法检查；至少先改掉注释里的错误论断。当前树经真 3.10.3 py_compile 全部通过，**无活病灶**，风险在「下一次改动能否被接住」。

### P1-4 static-server 代理分支可被绝对/协议相对 URL 劫持为任意主机中继（SSRF）

- **证据**（主控核读 + 子代理真实 PoC）：`docker/static-server.mjs:43` `const target = new URL(request.url, proxy.target)`——request.url 自带 authority（如 `http://169.254.169.254/latest/meta-data/` 或 `//evil.example/api/x`）时 base 被整体覆盖；`:47-51` 原样转发 method/headers/body 并把响应回传客户端。实测两种形态均返回 200。上一轮「畸形 URL 收口」（1434d9b）只修了静态分支（畸形百分号→400），同属「请求目标未收口」的代理子类漏了。
- **触发路径与缓解**：代理仅在 compose 形态启用（`docker-compose.prod.yml:148` 设置 PROXY_API_TARGET）；4000 端口对 compose 网络内所有容器开放，宿主侧 127.0.0.1:4173 对本机所有进程开放。离线内网部署显著降低可利用性，但任何能触达该端口的实体可借它探测/访问任意内网地址，且这是上一轮修复声明的直接残留。
- **修复**：构造 URL 后校验 `target.origin === new URL(proxy.target).origin`，不符返 400；或仅用 `pathname+search` 重组目标。

---

## P2（按主题归组，均子代理给出 file:line，重要项主控抽验）

### 数据正确性 / 并发

1. **record_id 格式分裂（两个子代理独立发现，可信度高）**：前端推理完成后的 flash 卡片用 3 段式 `tbbh|map_fid|name`（`frontend/src/utils/getUploadImg.js:182`），后端删除接口按 2 段式 `tbbh|name` 解析（`backend/applications/api/analysis.py:489-507`，历史列表 `:481` 产出的才是两段式）。推理成功到 `getMore()` 回填之间的窗口内点删除必然「记录不存在」。git 考古：双侧均始于初始化提交，非本分支回归。修复：flashCards 改 `${tbbh}|${name}`。
2. **KML 增量合并锁外执行 + 非原子写**：`kml_roi/service.py:65-75` 在父进程做共享 runtime.kml 的读-改-写，互斥锁在子进程 `kml_roi_infer.py:101` 才获取；`kml_merge.py:104` 直接 write 无临时文件+rename。并发提交可丢更新、后启动的子进程可能用错图斑集。F2 刚给 Excel 同步加了全程持锁，同一竞态在 KML 合并上未处理。
3. **Flask 侧 kml_roi 子进程无孤儿收口**：`service.py:172-178` 裸 `subprocess.run(timeout=3600)`；同批 e243755 给 mmseg 调用方加了 `_run_subprocess_with_cleanup`（`mmseg_inference_caller.py:269-294`），这条没跟上。父进程先死时孤儿持 flock 最长 90 分钟，期间所有推理 400/409——新锁把孤儿从「浪费算力」放大为「互斥不可用」。
4. **cleanup 保留集不含 `_vN` 变体**：`kml_roi/tiles.py:112-167` 的 `parse_year("2026_v2")` 为 None，keep 集不含 v2 产物；`backend/cleanup_change_outputs.py` 按既有手册跑会静默删掉 F1 修复（同 fid 多 Placemark）产出的第二图斑结果。
5. **预处理在 Flask 进程内整图读内存**：`kml_roi/preprocess.py:43-61` 经 `read_tiff_as_rgb`（两份全图副本，上限 500MB）+ 全尺寸 PNG 往返，在请求线程同步执行；对比切瓦片/推理本体都刻意挪进了子进程。

### 错误语义 / 提示

6. **miner kml-roi 500 分支回显内部异常原文**：`miner/server.js:1116-1121` `detail: message`（含完整命令行/绝对路径）；9f3754f 的「错误不回显」只改了 projects/auth 路由，漏掉自家核心推理端点。设备错误 400 分支的固定文案应保留。
7. **no_features 语义在前端被摊平**：后端对 `status==="no_features"` 返回 `success_api` 且 `data.message="No usable polygons in KML"`；前端 `getUploadImg.js:160-209` 不读 `payload.message`，用户只见笼统的"Flash 推理失败"。明确提示满足、原因丢失。
8. **downloadimgWithWords 的 fetch 无 catch 无超时**：`frontend/src/utils/download.js:8-33`，同批 1fead57 只补了 XHR 点的 onerror，漏了同文件唯一的 fetch 链，失败时 unhandled rejection 无任何用户反馈。
9. **预处理预览双层静默 catch**：`frontend/src/utils/preHandle.js:31-43` 对 createSrc 与 prePhotoHandle 均 `.catch(() => {})`，预览失败时勾选成功、预览区永远空白。
10. **登录页 reason 只在 created 消费**：`frontend/src/views/Login.vue:61-70`；已在登录页时迟到的 401 触发 `location.assign('/#/login?reason=expired')` 不合并既有 query，提示丢失且原 `redirect` 参数被覆盖。
11. **光谱页设备徽章硬编码 CPU 且被契约测试反向锁死**：`SpectralIndices.vue:15` + `analysisWorkflow.contract.test.mjs:46`（`assert.match(spectral, />CPU</)`）；1fead57 只环境化了 Segmentation/RunPanel，两页徽章在 GPU 部署下互相矛盾，该断言还会挡住将来的修复。

### 守卫 / 一致性

12. **CRLF 守卫测试定义在 `unittest.main()` 之后**：`docker/tests/test_source_isolation.py:173-184`，直接运行时静默跳过（实测直接跑 12 个、discover 13 个）；清单漏 `start-jiangxi-standalone.sh`、`init-sqlite-runtime.sh`、`seed-jiangxi-runtime.sh`、`init-mysql-runtime.sh`、`archive/start-analysis-worker-gpu.sh`。缓解：`.gitattributes` 已有 `*.sh eol=lf`。
13. **compose 与镜像内 healthcheck 双处定义无一致性守卫**：`docker-compose.prod.yml:82/105/135/160` 与 `standalone/healthcheck.sh:41` 本次同步改了，但无测试钉住探测端点/形态——「一处改一处漏」只靠人肉。GPU 契约测试（`test_jiangxi_gpu_contract.py:36-45`）已有同款断言先例可抄。
14. **miner 启动链子进程无超时**：`services/jiangxiGeoJsonSource.js` 的 geopandas execFile 与 powershell spawnSync、`server.js:161-181` 的 commandExists/pythonRunnable 均无 timeout，全部在 `initData()` → `app.listen` 之前；挂起则 miner 永不 bind。90min 超时修复只覆盖了推理 execFile 一处（同类未修实例模式）。
15. **15s fetch 超时无差别套用**：`services/projectBackend.js:18`、`services/authBackend.js:11` 含导出/备份恢复等慢操作，超 15s 用户看到 502 而后端任务实际成功，可能重复提交。
16. **小项**：`miner/package.json:19` `import:ndvi` 死链（scripts/ 目录从未存在）；`docker/entrypoint.sh:208` 向 miner 传死环境变量 GEOVIEW_BACKEND_URL（geoviewBackend.js 已删）；`frontend/test/download.contract.test.mjs` 不在任何 npm script 永不运行；`frontend/tests/segmentation-smoke.mjs:3` 注释引用从未存在的 upload-contract.test.mjs。
17. **GPU 链解押前置债**：`Dockerfile.jiangxi:55-56,113-119` GPU 分支 mmcv 2.1.0 vs fork/底座护栏 min 2.2.0（`dinov3_swinV1/mmseg/__init__.py:10`、`Dockerfile.jiangxi-runtime:95-96`）——构建门会响亮失败（非静默带病），属悬置 GPU 链的决策项，解押时二选一对齐。

---

## 验证门评估（测试网哪里有洞）

- **P1-1 的漏网原因**：`test_project_api.py` 无校验失败消息用例；Flask 侧退出码 3→ValueError 映射、kml_roi 推理端点越界路径拒绝均无直接用例。
- **P1-2 的佐证**：kml_update 零断言——死键写不出有效测试。
- **P1-3 即假绿本身**；P1-4 的代理分支在 static-server 回归测试中零覆盖（畸形 URL 测试只测静态分支）。
- **平台盲区**：`test_mmseg_worker.py` 三个最有价值的服务环测试与 `test_kml_roi_run_lock.py` 均 `skipUnless(AF_UNIX/fcntl)`，Windows 宿主上静默跳过——宿主绿不代表这些路径被验证过，权威跑法仍必须是 §5 的容器内跑。
- **前端门偏窄**：4 个新修复点仅「复选框受控化」有真实行为测试（smoke T5 真实点击），prehandle 载荷/hash 透传/重入守卫均为源码正则锁；`test:workflow` 等契约测试不在强制门内（AGENTS §5 只挂 build），叠加孤儿测试文件，实际护城河窄于提交信息声称的「契约冻结」。
- **miner**：96/96 无执行盲区；lint/format 清单缺 8 个测试文件（风格门盲区，非执行盲区）。

## 明确核实为干净的方面

- 上次 2 个 P0 修复端到端真实有效：prehandle/denoise 从受控复选框一路贯通到子进程（默认 0 行为不变有测试锁）；miner 推理/趋势弹窗入口、KML 上传→裸名回填→受控根提交链路、busy 409 映射、502 固定文案、NODE_ENV 三进程钉死全部核对无误。
- 设备契约（无 auto、无静默回退、非法即抛）、六类顺序、TBBH 主键、资产 348 红线（merge 只写派生 kml、默认 kmz 只读）、SECRET_KEY standalone 强制、/static 401 与 404 直通语义、T23 跨进程临时目录契约、EPIPE 教训在 worker serve 循环的落实——全部成立。
- 全部 docker/scripts/tools 的 .py 在真 3.10.3 下 py_compile 通过（当前树无活病灶）；8 个 .sh 全 LF + `bash -n` 过；`bash -n`/路径收口/写 runtime-env 唯一写者等契约逐项实测核对。
- 错误键契约（生产 `error`、消费 `error`/`error or message`、BFF 对 inference_runtime/runtime 双键兼容）两侧一致。

## 修复优先级建议

1. **小步快修（低风险，可随 PR 或紧随其后）**：P1-1 补 8 处 ValueError 分支；P1-3 守卫改真 3.10 子进程校验（至少先改错误注释）；P1-4 代理 origin 校验 + 补代理分支回归测试；P2-1 record_id 一行对齐。
2. **互斥链补齐**：P2-2 KML 合并上锁/原子写；P2-3 孤儿收口复用 `_run_subprocess_with_cleanup` 模式。
3. **守卫补齐**：P2-12 CRLF 测试位置+清单 glob 化；P2-13 healthcheck 一致性断言；前端 `test:workflow` 挂进强制门；删除/修正 P2-16 的死链与幽灵注释。
4. **体验类 P2 自行排期**（P2-6~11）；P1-2 死键裁决（落地或删除）需先定 BFF 链路是否要支持 KML 增量持久化——偏产品决策。
5. 修复时沿用并行子代理 + 文件所有权互斥 + 契约冻结 + 主控逐 diff 验收模式；涉及 docker/ 的改动 remember T22（重建镜像→容器内全套复跑）。

---

*审查方法与上轮一致（docs/code-review-20260914.md 前言）；本轮新经验：①「修复声明逐条对照实现」是本轮 4 个 P1 中 3 个的捕获手法（收口漏改/死键/守卫失效都是声明与实现的缝隙）；②两个独立子代理交叉发现同一问题（record_id）可视为免验证采信信号。*
