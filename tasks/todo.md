# 修复执行清单(code-review-20260919)

> 配套计划见 `tasks/plan.md`。纪律:一任务一 commit、提交即 push;Stop-the-Line——三网任一为红时不开新任务。
> 完成一项勾一项并回填 commit 号。

## Phase 0 —— 验证门回绿

- [ ] T0.1 [XS][P1-2] 超时断言对齐缩放公式,权威跑法 192 全绿 → commit: ______
- [ ] T0.2 [S][T1] 设备解析 mock 化,无 GPU 套件全绿(挂 GPU 复跑一次) → commit: ______

**Checkpoint 0**:backend 192 / miner 107 / frontend 34 全绿 ☐

## Phase 1 —— 验收阻断

- [ ] T1.1 [XS][P0-1] ImgShow 删除按钮 v-if 修复(契约测试先红后绿 + GUI 冒烟) → commit: ______
- [ ] T1.2 [S][P1-3] MAX_CONTENT_LENGTH 8.5GiB + 非 tif 尺寸检查(413 用例) → commit: ______
- [ ] T1.3 [M][P1-1+B1] 整图路径复用 extract_rgb_from_multiband + 归一化(uint16/4波段/2波段 等价性测试) → commit: ______

**Checkpoint 1**:权威跑法全绿 + 光谱页删除按钮 GUI 冒烟 ☐

## Phase 2 —— 安全批次

- [ ] T2.1 [S][M1+M9] miner 错误回显三处收口 → commit: ______
- [ ] T2.2 [S][S4] 登录失败限速(5 次锁 5 分钟) → commit: ______
- [ ] T2.3 [XS][S5] MySQL 弱口令回退置空 fail-fast → commit: ______
- [ ] T2.4 [XS][S6] interface 直通分支删除 → commit: ______
- [ ] T2.5 [XS][S8] show_result limit 钳制 → commit: ______
- [ ] T2.6 [M][S3] 上传魔数校验 → commit: ______
- [ ] T2.7 [M][S2] Flask 2.2.5 / Werkzeug 2.3.8 升级(临时容器全量回归) → commit: ______

**Checkpoint 2**:三网全绿 + 安全回归用例全过 ☐

## Phase 3 —— 整图链路补强

- [ ] T3.1 [M][B8] 假推理器单测四例(全 nodata/部分 nodata/失败行/超限) → commit: ______
- [ ] T3.2 [M][B2] nodata n 期联合剔除(先 Prove-It 证实现状) → commit: ______
- [ ] T3.3 [S][B3] 失败行写 255(先 Prove-It) → commit: ______
- [ ] T3.4 [XS][B4] 非 worker 批超时随行宽缩放 → commit: ______
- [ ] T3.5 [XS][B5] TimeoutExpired 保留 stderr + 3s/片环境变量化 → commit: ______
- [ ] T3.6 [XS][B7] cleanup --fid 对 ^U 名守卫 → commit: ______
- [ ] T3.7 [S][B6] cleanup --prune-unlinked N → commit: ______
- [ ] T3.8 [XS][P1-4+F8] 断链 catch 文案改「可能仍在后端执行」 → commit: ______
- [ ] T3.9 [M][F2] 上传预检 + 进度 + AbortController 取消 → commit: ______

**Checkpoint 3**:三网全绿 + 整图冒烟一次(协调 GPU 窗口) ☐

## Phase 4 —— 体验一致性 + 基建收尾

- [ ] T4.1 [XS][F3] flash before_img _src 回退 → commit: ______
- [ ] T4.2 [S][F4] 预处理 >500MB 前端预检 → commit: ______
- [ ] T4.3 [S][F5] running 守卫模块级单例 → commit: ______
- [ ] T4.4 [XS][F6] 契约断言字面量无关化 → commit: ______
- [ ] T4.5 [XS][F7] URL 拼接 String() 守卫 + 去前导斜杠 → commit: ______
- [ ] T4.6 [XS][M2] classification 路由级 authGuard 去重 → commit: ______
- [ ] T4.7 [S][M3] CSV 空单元格 NaN 拦截 → commit: ______
- [ ] T4.8 [XS][M5] catch 首行 tbbh 过期守卫 → commit: ______
- [ ] T4.9 [XS][M6] 服务端 years 优先口径 → commit: ______
- [ ] T4.10 [XS][M7] 404 空态中性化 → commit: ______
- [ ] T4.11 [XS][M8] axios timeout 15s → commit: ______
- [ ] T4.12 [XS][S7] /tmp 残留启动清理 → commit: ______
- [ ] T4.13 [XS][T2/T3/F1] AGENTS 权威跑法补记 + /opt/venv 钉死 + F1 台账补注 → commit: ______

**Checkpoint 4(最终门)**:三网全绿 + GUI 冒烟三页 + 报告回写处置台账 ☐

## 接受记录

- [x] S9(Windows 宿主锁失效):仅开发机直跑,容器不受影响——记录接受。

## 待裁决(不在本批)

- [ ] D1 整图异步作业化(P1-4/S1/B5 根治)
- [ ] D2 dev server → gunicorn(S1)
- [ ] D3 混合 KML 按 fid 过滤合并(B9)
- [ ] D4 km2 死字段删/落盘(M4)
- [ ] D5 GPU 链 mmcv 对齐(P2-17 沿旧)
- [ ] D6 生产镜像重建发布(生产生效)
