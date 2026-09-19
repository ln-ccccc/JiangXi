# 修复执行清单(code-review-20260919)——✅ 已全部执行完毕(2026-09-19)

> 配套计划见 `tasks/plan.md`。最终门:backend 229 / miner 110 / frontend 39 全绿。
> S9 记录接受;B3 证伪转回归钉;新增回归测试 45 个。

## Phase 0 —— 验证门回绿 ✅

- [x] T0.1 [XS][P1-2] 超时断言对齐缩放公式 → commit: 5b1435b
- [x] T0.2 [S][T1] 设备解析钉 cpu,解除无 GPU 假红(双门验证) → commit: f4819fb

## Phase 1 —— 验收阻断 ✅

- [x] T1.1 [XS][P0-1] ImgShow 删除按钮 v-if 分流(契约先红后绿) → commit: 22ac848
- [x] T1.2 [S][P1-3] MAX_CONTENT_LENGTH 8.5GiB + 非 tif 尺寸检查 → commit: dcb2146
- [x] T1.3 [M][P1-1+B1] 整图 tile 波段/归一化与联动路径同源 → commit: 9395ef6

## Phase 2 —— 安全批次 ✅

- [x] T2.1 [S][M1+M9] miner 错误回显收口(safeDeviceDetail + 裸文件名) → commit: 58eb4e4
- [x] T2.2 [S][S4] 登录失败限速 5 次锁 5 分钟 + 固定延迟 → commit: 99cfbbc
- [x] T2.3 [XS][S5] MySQL 弱口令回退置空 + fail-fast 门 → commit: 3eac18c
- [x] T2.4 [XS][S6] interface 直通分支删除 → commit: 19aea07
- [x] T2.5 [XS][S8] show_result limit 钳制 [1,100] → commit: 19aea07
- [x] T2.6 [M][S3] 上传魔数校验 → commit: 4d4caa5
- [x] T2.7 [M][S2] Flask 2.2.5 / Werkzeug 2.3.8(新旧双版本全量绿) → commit: ae93dad

## Phase 3 —— 整图链路补强 ✅

- [x] T3.1 [M][B8] 假推理器单测 5 例 + B3 证伪 → commit: 3097a59
- [x] T3.2 [M][B2] nodata 两期联合剔除(现状钉翻转) → commit: 2599a38
- [x] T3.3 [S][B3] **证伪**:未写块实测读 255(nodata 元数据生效),转回归钉 → 见 T3.1
- [x] T3.4 [XS][B4] 子进程批超时随行宽缩放(_batch_timeout 公式共用) → commit: ba682ac
- [x] T3.5 [XS][B5] 超时保留子进程输出尾部 + KML_ROI_EST_SEC_PER_TILE → commit: 4885baf
- [x] T3.6 [XS][B7] cleanup --fid U 前缀守卫 → commit: 6fc814a
- [x] T3.7 [S][B6] cleanup --prune-unlinked N → commit: 6fc814a
- [x] T3.8 [XS][P1-4+F8] 断链提示与真实失败区分 → commit: 083985f
- [x] T3.9 [M][F2] 上传预检 + 进度 + AbortController 取消 → commit: c0cbefd

## Phase 4 —— 一致性 + 基建收尾 ✅

- [x] T4.1 [XS][F3] flash 卡 _src 回退 → commit: a4ab546
- [x] T4.2 [S][F4] 预处理 >500MB 预检 → commit: d049cfb
- [x] T4.3 [S][F5] running 守卫模块级单例 → commit: d049cfb
- [x] T4.4 [XS][F6] 契约断言字面量无关化 → commit: 16764d6
- [x] T4.5 [XS][F7] URL 拼接守卫 + 去前导斜杠 → commit: 16764d6
- [x] T4.6-T4.11 [M2/M3/M5/M6/M7/M8] → commit: 0e609ee
- [x] T4.12 [XS][S7] /tmp 残留启动清扫 → commit: 3e82f47
- [x] T4.13 [XS][T2/T3/F1] AGENTS 权威跑法 + 台账 → commit: 167fa50

## 计划外抓获(测试当场暴露)

- items_handle 只变异不返回 → /api/analysis/show 的 data 恒为 null → 已修(commit 19aea07)

## 接受记录

- [x] S9(Windows 宿主锁失效):仅开发机直跑,容器不受影响——记录接受。

## 待裁决(不在本批,同 plan.md 决策项)

- [ ] D1 整图异步作业化(P1-4/S1/B5 根治)
- [ ] D2 dev server → gunicorn(S1)
- [ ] D3 混合 KML 按 fid 过滤合并(B9)
- [ ] D4 km2 死字段删/落盘(M4)
- [ ] D5 GPU 链 mmcv 对齐(P2-17 沿旧)
- [ ] D6 生产镜像重建发布(生产生效;本批 22 个 commit 均只在代码库,生产容器未动)
