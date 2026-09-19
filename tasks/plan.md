# 第三轮审查修复计划(code-review-20260919 → fix)

> 方法来源:[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) 的五个工程 skill,逐条落到本计划的纪律上:
>
> | skill | 在本计划中的落地 |
> |---|---|
> | `planning-and-task-breakdown` | 全部工作分解为 34 个独立可验证任务(尺寸 XS/S/M),每任务带 ≤3 条验收标准 + 明确验证命令 + 依赖关系;每阶段一个检查点 |
> | `test-driven-development` | 每个缺陷修复先立复现测试(Prove-It:先红后绿);报告中标【待验证】的 P2 先写「钉现状」用例,现状与报告不符则任务转为回归钉 |
> | `incremental-implementation` | 一任务一垂直切片,单任务改动 ≤150 行(含测试),独立可验证、独立可回滚,禁止跨任务攒批 |
> | `git-workflow-and-versioning` | 原子提交(conventional commits),每 commit 立即 push;提交信息注明影响面与「未触碰」范围 |
> | `debugging-and-error-recovery` | **Stop-the-Line 制度化**(P1-2 的直接教训):测试网为红时禁止任何新提交;修复必须含「防回潮」测试 |

## 一、概述

- **输入**:`docs/code-review-20260919.md` —— P0×1、P1×4、P2×27(后端 B1-B9 / 前端 F1-F8 / miner M1-M9 / 安全 S1-S9 / 测试基建 T1-T3,含交叉)。
- **目标**:32 个发现全部处置:31 个修复 + 1 个记录在案接受(S9,仅开发机直跑受影响);另有 6 个决策项单列待裁决。
- **不在本批范围**:生产容器热更/镜像重建(D6)、整图异步作业化(D1)等架构级改造;GPU 链 mmcv 对齐(D5)沿旧悬置。
- **测试基线**:backend 192(P1-2 修后全绿)/ miner 107 / frontend 34。

## 二、策略决策(及理由)

1. **验证门前置(Phase 0)**:先修 P1-2 让套件回绿,再做 T1 设备 mock 化让验证车辆不依赖 GPU(用户 GPU 正被实测占用)。此后所有任务的常规验证不挂 `--gpus all`。
2. **验收标准上限 3 条**:超过 3 条说明任务太大,继续拆。
3. **验证命令写死**:后端一律容器权威跑法(见 §五),杜绝「本机 interpreter 假绿」四连教训。
4. **提交节奏**:每任务一 commit,格式 `fix|test|docs(scope): 描述——动机(报告编号)`,提交即 push。
5. **生产零接触**:本批只动代码与测试;生产容器 `geoview-jiangxi-gpu-20260916` 实测中不干扰,生效走 D6 统一发布。

## 三、任务列表

尺寸:XS ≤10 行, S ≤50 行, M ≤150 行(均含测试)。

### Phase 0 —— 验证门回绿(阻塞一切,Stop-the-Line)

| ID | 尺寸 | 任务 | 验收标准(≤3) | 验证 | 文件 | 依赖 |
|---|---|---|---|---|---|---|
| T0.1 | XS | **P1-2** 超时断言对齐缩放公式:`test_kml_roi_subprocess_cleanup.py:96` 改为断言 `min(14400, max(3600, tiles*2*3))`,覆盖 3600 下限与 14400 上限两情形 | ① 断言含公式两端;② 权威跑法 192 全绿 | 容器权威跑法 | test_kml_roi_subprocess_cleanup.py | 无 |
| T0.2 | S | **T1** 设备解析在 API 测试层 mock 化,解除 5 个测试对真实 CUDA 的耦合 | ① 同一镜像不挂 `--gpus all` 套件全绿;② 挂 GPU 权威跑法仍全绿 | 同上(跑两次:有/无 GPU) | test_*.py(设备相关 5 个)+ 可能的测试夹具 | T0.1 |

**Checkpoint 0**:三网全绿(backend 192 / miner 107 / frontend 34)。此后任意 commit 前套件必须为绿。

### Phase 1 —— 验收阻断(P0/P1)

| ID | 尺寸 | 任务 | 验收标准(≤3) | 验证 | 文件 | 依赖 |
|---|---|---|---|---|---|---|
| T1.1 | XS | **P0-1** ImgShow 删除按钮 `v-if="item.record_id || (!item.unlinked && item.id)"`;契约测试**先行**(对新断言 RED→GREEN):光谱历史走 `id`、kml_roi 走 `record_id`、未联动卡仍隐藏 | ① 新契约断言先红后绿;② frontend 34 绿;③ GUI 冒烟:光谱页历史卡有删除按钮且可删,Segmentation 未联动卡无按钮 | `npm test` + 手工 GUI 冒烟 | ImgShow.vue、analysisWorkflow.contract.test.mjs | T0.2 |
| T1.2 | S | **P1-3** `BaseConfig.MAX_CONTENT_LENGTH = int(8.5*1024**3)`;file.py 对非 TIFF 补 seek/tell 上限。测试用小上限覆写验证 413 与无落盘残留 | ① 超限请求 413 且 Werkzeug 提前掐断;② 非 tif 超限拒绝;③ 磁盘无残留 | 后端套件 + 新增用例 | configs/config.py、api/file.py + 新测试 | T0.2 |
| T1.3 | M | **P1-1 + B1** 整图逐 tile 处复用 `extract_rgb_from_multiband` + 非 uint8 2%-98% 归一化(与联动路径同一函数,2 波段灰度复制一并根治)。TDD:先构造 uint16/4 波段/2 波段小 tif 写等价性测试(红),再修(绿) | ① 三种输入整图与联动路径对同一图斑产出相同 tile 字节;② 3 波段 uint8 无回归;③ 用例落入假推理器框架(为 T3.1 铺路) | 后端套件 + 新增用例 | kml_roi/pipeline.py + 新测试 | T0.2 |

**Checkpoint 1**:权威跑法全绿 + GUI 冒烟(P0-1)。此时 P0/P1 四项全清,可先行向甲方交付口径。

### Phase 2 —— 安全批次

| ID | 尺寸 | 任务 | 验收标准(≤3) | 验证 | 文件 | 依赖 |
|---|---|---|---|---|---|---|
| T2.1 | S | **M1+M9** miner 400 设备分支与 400/500 遗留路径不再回显完整命令行/绝对路径(固定文案或仅 stderr 尾部/裸名) | ① 三个分支响应体 grep 不到 `/` 开头路径与 `Command failed:`;② miner 107 绿 + 测试更新 | `cd miner && npm test` | miner/server.js + 测试 | T0.2 |
| T2.2 | S | **S4** 登录失败限速:内存 dict,5 次锁 5 分钟 + 固定延迟 | ① 第 6 次失败被锁;② 锁窗口后恢复;③ 有测试 | 后端套件 + 新增用例 | auth.py + 新测试 | T0.2 |
| T2.3 | XS | **S5** MySQL 弱口令回退 "123456" 置空 + fail-fast(与 SECRET_KEY 同款门) | ① grep 无 "123456";② 未注入口令时启动即报错(测试锁源码+行为) | 后端套件 | configs/config.py + 测试 | T0.2 |
| T2.4 | XS | **S6** 删除 interface 层 `os.path.exists(text)` 直通分支 | ① 分支消失;② 现有 interface 测试不回归 | 后端套件 | interface/analysis.py | T0.2 |
| T2.5 | XS | **S8** `show_result` limit 钳制 `max(1, min(100, limit))`(复制 kml_roi_history 写法) | ① limit=10^9 返回被钳;② 有测试 | 后端套件 | api/analysis.py + 测试 | T0.2 |
| T2.6 | M | **S3** 上传内容魔数校验:tif 头 4 字节 + 非 tif 白名单内容探针,拒绝任意数据改名入库 | ① 随机数据改名 .tif → 400 且无落盘;② 真 tif/png 不受影响;③ 有测试 | 后端套件 + 新增用例 | tiff_processor.py、api/file.py + 测试 | T1.2 |
| T2.7 | M | **S2** 依赖升 `Flask==2.2.5 + Werkzeug==2.3.8`(2.2 系内)。验证:临时容器内 `pip install` 新版本后跑 192 全量回归;生产生效走 D6 | ① requirements 已钉新版本;② 临时容器全量 192 绿 | 容器内 pip 升级后权威跑法 | requirements.txt | T0.2 |

**Checkpoint 2**:三网全绿 + 安全回归用例(413/魔数/限速/回显)全过。

### Phase 3 —— 整图链路补强

| ID | 尺寸 | 任务 | 验收标准(≤3) | 验证 | 文件 | 依赖 |
|---|---|---|---|---|---|---|
| T3.1 | M | **B8** 假推理器单测钉住流式拼接四例:全 nodata、部分 nodata、失败行、超限(4-billion-pixel cap)。T1.3 的用例并入此框架 | ① 四例各有一个用例;② 全部先钉**现状**再暴露语义缝 | 后端套件 | kml_roi/pipeline.py 测试侧 | T1.3 |
| T3.2 | M | **B2** nodata n 期联合剔除(缓存 `row_raw_n` 联合剔除)。报告标【待验证】:先写用例证实/证伪,证伪则转回归钉 + 台账 | ① 两期覆盖不一致用例:黑边不再判水体;② 深色水体非大面积不误剔 | 后端套件 | kml_roi/pipeline.py | T3.1 |
| T3.3 | S | **B3** 整行失败写全 255 mask 行(防 GIS 统计虚增草地)。同上先证实现状 | ① 失败行读出 255;② 有测试 | 后端套件 | kml_roi/pipeline.py | T3.1 |
| T3.4 | XS | **B4** 非 worker 路径批超时随行宽缩放(对齐 worker 路径 `3.0*len(names)`) | ① 两路径公式一致;② 有测试 | 后端套件 | mmseg_inference_caller.py + 测试 | T0.2 |
| T3.5 | XS | **B5(轻量部分)** `TimeoutExpired` 时保留 e.output/e.stderr 尾部进错误信息;3s/片估算改环境变量可调。冷启动总时长问题留 D1 | ① 超时报错非空;② 估算系数可注入;③ 有测试 | 后端套件 | mmseg_inference_caller.py、service.py + 测试 | T0.2 |
| T3.6 | XS | **B7** cleanup `--fid` 对 `^U` 名守卫(与主循环同正则) | ① `--fid U123` 被拒并提示;② 有测试 | 后端套件 | cleanup_change_outputs.py + 测试 | T0.2 |
| T3.7 | S | **B6** cleanup 增 `--prune-unlinked N`(按 mtime 保留最近 N 个 U 产物) | ① N 之外的 U 目录被清;② 误删防护(缺省不动);③ 有测试 | 后端套件 | cleanup_change_outputs.py + 测试 | T3.6 |
| T3.8 | XS | **P1-4 最小修(含 F8)** 断链 catch 区分网络错误:「连接已中断,任务可能仍在后端执行,请稍后刷新历史查看」 | ① 文案不再断言失败;② 契约测试锁文案 | `npm test` | getUploadImg.js + 契约测试 | T0.2 |
| T3.9 | M | **F2** 8GB 上传:选文件即 `file.size` 预检 + `onUploadProgress` 百分比 + AbortController 取消 | ① >8.5GB 秒拒不上传;② 进度可见;③ 可取消;④ 契约测试 | `npm test` | getUploadImg.js、api/requestfile.js + 测试 | T1.2 |

**Checkpoint 3**:三网全绿 + 手工整图冒烟一次(需 GPU 容器,与用户协调窗口;中型影像即可)。

### Phase 4 —— 体验一致性 + 测试基建收尾

| ID | 尺寸 | 任务 | 验收标准(≤3) | 验证 | 文件 | 依赖 |
|---|---|---|---|---|---|---|
| T4.1 | XS | **F3** flash 卡 before_img `_src` 缺失回退(handleImageError 回填 afterUrl) | ① `_src` 404 时左图回退;② 契约断言 | `npm test` | getUploadImg.js + 测试 | T0.2 |
| T4.2 | S | **F4** 勾选预处理且 >500MB 时前端预检直拒,不再整包重传 | ① 秒拒并提示「大影像不支持预处理预览」;② 有断言 | `npm test` | preHandle.js + 测试 | T0.2 |
| T4.3 | S | **F5** running 守卫提升为模块级单例,路由切换不失效 | ① 模拟切换后再发起被拦;② 有断言 | `npm test` | Segmentation.vue、getUploadImg.js | T0.2 |
| T4.4 | XS | **F6** 「工作流保持江西同步链路」断言字面量无关化(对齐同批其它断言) | ① 引号风格变更不再打红;② 34 绿 | `npm test` | analysisWorkflow.contract.test.mjs | T0.2 |
| T4.5 | XS | **F7** 非 flash 分支 URL 拼接 `String()` 守卫 + 去前导斜杠(对齐 flash 分支) | ① 字段异常不出 `undefined` URL;② 有断言 | `npm test` | getUploadImg.js + 测试 | T0.2 |
| T4.6 | XS | **M2** classification 路由级 authGuard 删除(保留 app.use 全局),测试改断言挂载方式 | ① 每请求一次 session 往返;② miner 107 绿 | `cd miner && npm test` | miner/server.js + 测试 | T0.2 |
| T4.7 | S | **M3** parseClassificationMatrixCsv 空单元格映射 NaN(走 isFinite 拦截),补用例 | ① 空 CSV 格显示错误而非假 0%;② 有用例 | `cd miner && npm test` | classificationAssets.js + 测试 | T0.2 |
| T4.8 | XS | **M5** 分类面板 catch 首行加 tbbh 过期守卫(对齐成功分支) | ① 旧图斑失败不覆盖新图斑;② 有断言 | `cd miner && npm test` | EcologyDiagnosisPanels.vue | T0.2 |
| T4.9 | XS | **M6** 服务端只回一套口径:有 `years` 时忽略 `pair` | ① 混存时年份标签与服务端一致;② 有测试 | `cd miner && npm test` | miner/server.js + 测试 | T0.2 |
| T4.10 | XS | **M7** 404「暂无推理结果」改中性空态,不再渲染红错 | ① 348 未推理图斑打开非红;② 有断言 | `cd miner && npm test` | miner/server.js、EcologyDiagnosisPanels.vue | T0.2 |
| T4.11 | XS | **M8** loadClassification 加 `{ timeout: 15000 }` | ① 半开连接 15s 处理;② 有断言 | `cd miner && npm test` | EcologyDiagnosisPanels.vue | T0.2 |
| T4.12 | XS | **S7** 启动时清理 /tmp 超 1 天的 `kml-roi-infer-*` 残留 | ① 启动清扫生效;② 有测试(临时目录注入) | 后端套件 | service.py + 测试 | T0.2 |
| T4.13 | XS | **T2/T3/F1 文档收尾**:AGENTS.md 补权威跑法(含解释器路径)+ /opt/venv 钉死说明 + F1 git 历史误导台账补注;可选:落 `scripts/verify-all.sh` 一键三门 | ① AGENTS 三处补记;② 新人按文档可直接跑绿 | 文档走查 | AGENTS.md、scripts/(可选) | T0.2 |

**Checkpoint 4(最终门)**:三网全绿 + GUI 冒烟三页 + AGENTS 更新 + 审查报告回写各发现 → commit 号(处置台账闭合)。

### 单列接受(不做任务)

- **S9**(Windows 宿主无 fcntl 时推理锁失效):仅开发机直跑场景,容器生产不受影响——记录接受,台账注明。

## 四、决策项(需用户裁决,不在本批排期)

| ID | 事项 | 关联发现 | 一句话建议 |
|---|---|---|---|
| D1 | 整图异步作业化(job + 轮询 `kml_roi_history`) | P1-4 根治、S1 根治、B5 根治 | 若甲方还要压大影像,值得做;否则 T3.8 文案缓解够用 |
| D2 | dev server → gunicorn | S1 | 若甲方可能查生产 WSGI 则做,半天工作量 |
| D3 | 混合 KML 按 fid 过滤合并(merge_kml_increment 加 allow_fid) | B9 | 行为变更涉及产品口径,需裁决「联动部分白算」是否可接受 |
| D4 | `confusion_matrix.km2` 死字段:删 or 管线落盘 | M4 | 建议删(简单优先),`map_fid: Number(fid)` 一并对齐 |
| D5 | GPU 链 mmcv 2.1.0 vs 2.2.0 对齐 | P2-17 沿旧 | 两轮悬置,继续挂起 |
| D6 | 生产镜像重建发布(S2/S3/P1-1 等生产生效) | 本批全部 | 需停机窗口 + docker/ 全套 T22 复跑 + 四大重建陷阱清单走一遍 |

## 五、验证命令(权威,写死)

```bash
# 后端(容器权威跑法;T0.2 落地后常规验证可不挂 --gpus all)
MSYS_NO_PATHCONV=1 docker run --rm --gpus all \
  --entrypoint /opt/conda/envs/MMSeg310/bin/python \
  -e STANDALONE_MODE= \
  -v "D:/项目/JiangXi/JiangXi-Platform/backend:/app/backend" \
  -w /app/backend geoview-jiangxi:jiangxi-gpu-20260916-fixes \
  -m unittest discover -s . -p "test_*.py"

# miner / frontend(宿主)
cd miner && npm test
cd frontend && npm test
```

三陷阱红线:解释器必须是 MMSeg310(/opt/venv 假象)、`STANDALONE_MODE=` 必须置空、Git Bash 必须 `MSYS_NO_PATHCONV=1`。

## 六、风险与缓解

| 风险 | 缓解 |
|---|---|
| 依赖升级(S2)破坏 192 | 2.2 系内小版本,临时容器先验;破坏则回滚 pin 单独复盘 |
| B2/B3 报告判断与实况不符(标【待验证】) | Prove-It:先写钉现状用例;证伪则任务转回归钉 + 报告勘误,不强修 |
| 用户 GPU 实测与容器测试抢资源 | T0.2 后常规验证不挂 GPU;仅 Checkpoint 3 冒烟需协调窗口 |
| 直推 main 时验证门再失守(P1-2 反例) | Stop-the-Line 写进每个任务的验证栏;检查点强制三网绿;T4.13 可选一键脚本把门机械化 |
| 代码修了、生产容器仍是旧行为 | 明示本批不动生产(D6);交付口径里注明「生产生效待 D6」 |

## 七、完成定义(Definition of Done)

1. 32 个发现逐条有 commit 或台账记录(31 修 + S9 接受);
2. 三网全绿且检查点 0-4 全部留有运行记录;
3. 审查报告回写处置结果(发现 → commit 号);
4. AGENTS.md 权威跑法补记完成;
5. 决策项 D1-D6 呈报用户,附建议。

## 八、开放问题(开工前需确认)

- **Q1 分支策略**:验收期惯例直推 main(每 commit 带验证门),还是开 `fix/code-review-20260919` 收口后走 PR(需用户手动建 PR)?**建议:直推 main**,与验收期惯例一致、避免 PR 渠道退化风险。
- **Q2 批次切分**:Phase 0-3(验收阻断+安全+链路)先行交付甲方,Phase 4(体验一致性)二批?还是四阶段连做?**建议:连做**,总量约 34 个小任务、多为 XS/S。
- **Q3 D4/D6 裁决时机**:km2 字段与镜像重建可现在定,也可等 Phase 0-3 完成后再定。
