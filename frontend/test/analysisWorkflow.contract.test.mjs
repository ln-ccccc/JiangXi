import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const testDirectory = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testDirectory, "..");
const read = (...segments) =>
  fs.readFileSync(path.join(frontendRoot, ...segments), "utf8");

const segmentation = read("src", "views", "mainfun", "Segmentation.vue");
const spectral = read("src", "views", "mainfun", "SpectralIndices.vue");
// 组件拆分后执行按钮/运行状态标记随 RunPanel 下沉，断言需指向实际所在文件
const runPanel = read("src", "views", "mainfun", "segmentation", "RunPanel.vue");
const imageShow = read("src", "components", "ImgShow.vue");
const tabInfo = read("src", "components", "Tabinfor.vue");
const bottomInfo = read("src", "components", "Bottominfor.vue");
const theme = read("src", "assets", "css", "theme-dark.css");
const uploadUtility = read("src", "utils", "getUploadImg.js");
const preHandleUtility = read("src", "utils", "preHandle.js");
const authRedirect = read("src", "utils", "authRedirect.js");
const loginView = read("src", "views", "Login.vue");

const workflowPages = [segmentation, spectral];
const workflowSource = workflowPages.join("\n");
const productionSource = [
  workflowSource,
  imageShow,
  tabInfo,
  bottomInfo,
  theme,
  uploadUtility,
].join("\n");

test("两类分析页都呈现江西同步四步工作流", () => {
  for (const source of workflowPages) {
    assert.match(source, /class="[^"]*\banalysis-workflow\b[^"]*"/);
    assert.match(source, /workflow-step__number">01<\/span><span>数据源/);
    assert.match(source, /workflow-step__number">02<\/span><span>参数设置/);
    assert.match(source, /workflow-step__number">03<\/span><span>执行分析/);
    assert.match(source, /workflow-step__number">04<\/span><span>结果预览/);
    assert.match(source, /江西/);
    assert.match(source, /同步分析/);
  }
  assert.match(segmentation, /VUE_APP_JIANGXI_INFERENCE_DEVICE/);
  assert.match(spectral, />CPU</);
});

test("工作流保持江西同步链路并使用容器设备配置", () => {
  assert.match(
    runPanel,
    /seg\.upload\('地物分类','semantic_segmentation'\)/,
  );
  assert.match(spectral, /@click="startCompute"/);
  assert.match(spectral, /this\.createSrc\(formData\)\.then/);
  assert.match(spectral, /return this\.imgUpload\(/);
  assert.match(uploadUtility, /VUE_APP_JIANGXI_INFERENCE_DEVICE/);
  assert.doesNotMatch(productionSource, /\/api\/inference\/jobs/i);
  assert.doesNotMatch(productionSource, /自动\s*GPU|GPU\s*回退|自动设备选择/i);
});

test("没有 tif 或 tiff 时两个执行按钮都明确禁用", () => {
  // [^"]* 允许运行中守卫追加在空列表判断之后（复审批次 C4）
  assert.match(
    runPanel,
    /<el-button[^>]*:disabled="seg\.fileList\.length\s*===\s*0[^"]*"[^>]*>/s,
    "地物分类执行按钮在 RunPanel，拆分后仍需禁用语义",
  );
  assert.match(
    spectral,
    /<el-button[^>]*:disabled="fileList\.length\s*===\s*0[^"]*"[^>]*>/s,
  );
  for (const source of workflowPages) {
    assert.match(source, /请先选择 tif \/ tiff 影像/);
  }
});

test("页面暴露等待、失败和部分成功的可感知状态", () => {
  assert.match(runPanel, /aria-live="polite"/);
  assert.match(spectral, /aria-live="polite"/);
  assert.match(spectral, /data-state="idle"/);
  assert.match(spectral, /data-state="error"/);
  assert.match(spectral, /data-state="partial"/);
  assert.match(spectral, /计算失败/);
  assert.match(spectral, /同步部分失败/);
  assert.match(uploadUtility, /Flash 部分成功/);
  assert.match(uploadUtility, /Flash 推理失败/);
  assert.match(
    spectral,
    /v-if="runState === 'idle' && !fileList\.length"/,
    "清空已完成队列后仍应保留成功或部分成功状态",
  );
});

test("地物分类渲染真实运行状态而不是静态状态说明", () => {
  assert.match(segmentation, /analysisRunState:\s*"idle"/);
  assert.match(segmentation, /analysisRunMessage:\s*"请先选择 tif \/ tiff 影像。"/);
  assert.match(
    runPanel,
    /<p\s+:data-state="seg\.analysisRunState">\s*\{\{ seg\.analysisRunMessage \}\}\s*<\/p>/s,
    "运行状态标记拆分后在 RunPanel，仍需绑定真实状态",
  );
  assert.doesNotMatch(segmentation, /<span data-state="(?:partial|error)">/);
  assert.match(segmentation, /this\.analysisRunState\s*=\s*"ready"/);
  assert.match(segmentation, /this\.analysisRunState\s*=\s*"error"/);
  assert.match(segmentation, /this\.analysisRunState\s*=\s*"idle"/);
});

test("地物分类工具链按真实 Promise 分支更新 running、partial、success 与 error", () => {
  const runningIndex = uploadUtility.search(/setAnalysisRunState\(\s*this,\s*'running'/);
  const createSrcIndex = uploadUtility.indexOf("return this.createSrc(formData).then");
  assert.ok(runningIndex >= 0, "发起上传前必须进入 running");
  assert.ok(createSrcIndex > runningIndex, "running 必须早于 createSrc 请求");
  assert.match(uploadUtility, /for \(const tifPath of rawTiffPaths\)/);
  assert.match(uploadUtility, /await kmlRoiInfer\(/);
  assert.doesNotMatch(uploadUtility, /Promise\.all\(inferenceRequests\)/);
  assert.match(uploadUtility, /status: 'rejected'/);
  assert.match(
    uploadUtility,
    /if \(totalFailureCount > 0\) \{[\s\S]*setAnalysisRunState\(this, 'partial'/,
  );
  assert.match(
    uploadUtility,
    /\} else \{[\s\S]*setAnalysisRunState\(this, 'success'/,
  );
  assert.match(
    uploadUtility,
    /rawTiffPaths\.length === 0[\s\S]*setAnalysisRunState\(this, 'error'/,
  );
  assert.match(
    uploadUtility,
    /Flash 推理失败，未生成任何结果[\s\S]*setAnalysisRunState\(this, 'error'/,
  );
  assert.match(
    uploadUtility,
    /\.catch\(\(err\) => \{[\s\S]*setAnalysisRunState\(this, 'error'/,
  );
  assert.match(uploadUtility, /\.finally\(\(\) => \{/);
  assert.match(
    uploadUtility,
    /if \(this\.analysisRunState === 'running'\)[\s\S]*setAnalysisRunState\(/,
  );
});

test("flash 卡片 record_id 冻结为 2 段式 tbbh|name（与后端删除接口对齐）", () => {
  // 后端 /api/analysis/kml_roi_history/item 按 record_id.split("|", 1) 解析，
  // 3 段式 tbbh|map_fid|name 在删除时必然「记录不存在」
  const recordIdIndex = uploadUtility.indexOf("record_id:");
  assert.ok(recordIdIndex >= 0, "flash 卡片必须携带 record_id");
  const recordIdSource = uploadUtility.slice(recordIdIndex, recordIdIndex + 80);
  assert.match(recordIdSource, /record_id:\s*`\$\{tbbh\}\|\$\{name\}`/);
  assert.doesNotMatch(uploadUtility, /record_id:\s*`\$\{tbbh\}\|\$\{mapFid\}/);
});

test("预处理预览失败必须给出可见提示而不是静默吞掉", () => {
  // 双层静默 catch 曾导致「勾选成功、预览区永远空白」且无任何解释
  assert.doesNotMatch(preHandleUtility, /\.catch\(\(\) => \{\}\)/);
  assert.match(preHandleUtility, /\$message\?\.\s*warning\?\.\(\s*['"]预处理预览生成失败/);
  assert.match(preHandleUtility, /\$message\?\.\s*warning\?\.\(\s*['"]预处理原图上传失败/);
});

test("kmlRoiInfer 载荷携带预处理状态（与后端契约冻结：prehandle / denoise）", () => {
  const payloadStart = uploadUtility.indexOf("await kmlRoiInfer({");
  assert.ok(payloadStart >= 0, "必须经 kmlRoiInfer 发起地物分类推理");
  const payloadSource = uploadUtility.slice(payloadStart, payloadStart + 600);
  assert.match(
    payloadSource,
    /prehandle:\s*this\.uploadSrc\.prehandle/,
    "载荷必须回传 uploadSrc.prehandle（值域 0/2/4）",
  );
  assert.match(
    payloadSource,
    /denoise:\s*this\.uploadSrc\.denoise/,
    "载荷必须回传 uploadSrc.denoise（值域 0/3/5）",
  );
});

test("地物分类结果图片加载失败时提供可见错误而不是空白", () => {
  assert.match(imageShow, /@error="handleImageError/);
  assert.match(imageShow, /结果图片加载失败/);
  assert.match(imageShow, /legacySession/);
});

test("地物分类页面在打开期间刷新会话并在离开时清理定时器", () => {
  assert.match(segmentation, /legacySession/);
  assert.match(segmentation, /setInterval\(/);
  assert.match(segmentation, /10 \* 60 \* 1000/);
  assert.match(segmentation, /beforeUnmount\(\)/);
});

test("结果区提供有方向的空态、历史操作和正确简体中文", () => {
  assert.match(imageShow, /尚无分析结果/);
  assert.match(imageShow, /请先在上方选择 tif \/ tiff 影像并执行分析/);
  assert.match(imageShow, /原始影像/);
  assert.match(imageShow, /分析结果/);
  assert.match(imageShow, /下载结果/);
  assert.match(imageShow, /删除该组/);
  assert.doesNotMatch(productionSource, /�/);
});

test("地物分类图例对服务端结果类型可达", () => {
  assert.match(imageShow, /v-if="isLandClassification\(item\)"/);
  assert.match(imageShow, /isLandClassification\(item\)\s*{/);
  assert.match(imageShow, /地物分类/);
  assert.match(imageShow, /semantic_segmentation/);
  for (const label of ["草地", "林地", "建筑", "道路", "裸地", "水体"]) {
    assert.match(imageShow, new RegExp(label));
  }
});

test("会话过期跳转携带 hash 路由且登录页消费 reason", () => {
  // 路由是 hash 模式：redirect 必须取自 location.hash，跳转目标是 /#/login，
  // 否则 query 无人消费（历史缺陷：redirect 恒为 "/"、reason 丢失）。
  assert.match(authRedirect, /window\.location\.hash/);
  assert.match(authRedirect, /params\.set\("redirect",\s*hashRoute\)/);
  assert.match(authRedirect, /params\.set\("reason",\s*reason\)/);
  assert.match(authRedirect, /#\/login\?\$\{params\.toString\(\)\}/);
  // 已在登录页时迟到的 401 重跳转必须合并既有 query，不得覆盖丢失 redirect
  assert.match(authRedirect, /new URLSearchParams\(search\)/);
  assert.match(authRedirect, /pathname\.startsWith\("\/login"\)/);

  // 登录页必须把 reason 呈现为可见文案，而不是无声吞掉；
  // 且必须 watch 响应式消费（组件不重建，迟到的 reason 只在 created 读一次会丢）
  assert.match(loginView, /"\$route\.query\.reason":\s*\{/);
  assert.match(loginView, /immediate:\s*true/);
  assert.match(loginView, /登录已过期，请重新登录/);
  assert.match(loginView, /v-if="sessionNotice"/);
  assert.match(loginView, /this\.\$router\.replace\(this\.\$route\.query\.redirect \|\| "\/segmentation"\)/);
});

test("分析工作流在三档窄屏和 reduced-motion 下保持可用", () => {
  const styleSource = [workflowSource, imageShow, tabInfo, theme].join("\n");
  assert.match(styleSource, /@media\s*\(max-width:\s*1100px\)/);
  assert.match(styleSource, /@media\s*\(max-width:\s*768px\)/);
  assert.match(styleSource, /@media\s*\(max-width:\s*480px\)/);
  assert.match(styleSource, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  assert.match(styleSource, /:focus-visible/);
});

test("工作流样式只使用江西令牌且页脚不再跳转外部站点", () => {
  assert.match(workflowSource, /var\(--jx-/);
  assert.doesNotMatch([workflowSource, imageShow].join("\n"), /#409eff/i);
  assert.match(bottomInfo, /江西省矿山生态修复智能监测平台/);
  assert.doesNotMatch(bottomInfo, /github|https?:\/\//i);
});

test("执行入口带运行中重入守卫，防止上传阶段并发重复提交推理", () => {
  // 上传阶段走 requestfile 无全屏锁，按钮可再次点击 → 并发两组推理子进程
  // 交叉写共享产物目录（复审批次 C4）
  assert.match(uploadUtility, /analysisRunState === 'running'/);
  assert.match(uploadUtility, /reason: 'busy'/);
  assert.match(runPanel, /seg\.analysisRunState === 'running'/);
  assert.match(spectral, /runState === "running"/);
  assert.match(spectral, /:disabled="fileList\.length === 0 \|\| runState === 'running'"/);
});
