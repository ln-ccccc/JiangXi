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
const imageShow = read("src", "components", "ImgShow.vue");
const tabInfo = read("src", "components", "Tabinfor.vue");
const bottomInfo = read("src", "components", "Bottominfor.vue");
const theme = read("src", "assets", "css", "theme-dark.css");
const uploadUtility = read("src", "utils", "getUploadImg.js");

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
    segmentation,
    /upload\('地物分类','semantic_segmentation'\)/,
  );
  assert.match(spectral, /@click="startCompute"/);
  assert.match(spectral, /this\.createSrc\(formData\)\.then/);
  assert.match(spectral, /return this\.imgUpload\(/);
  assert.match(uploadUtility, /VUE_APP_JIANGXI_INFERENCE_DEVICE/);
  assert.doesNotMatch(productionSource, /\/api\/inference\/jobs/i);
  assert.doesNotMatch(productionSource, /自动\s*GPU|GPU\s*回退|自动设备选择/i);
});

test("没有 tif 或 tiff 时两个执行按钮都明确禁用", () => {
  for (const source of workflowPages) {
    assert.match(
      source,
      /<el-button[^>]*:disabled="(?:!fileList\.length|fileList\.length\s*===\s*0)"[^>]*>/s,
    );
    assert.match(source, /请先选择 tif \/ tiff 影像/);
  }
});

test("页面暴露等待、失败和部分成功的可感知状态", () => {
  for (const source of workflowPages) {
    assert.match(source, /aria-live="polite"/);
  }
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
  assert.match(segmentation, /<p\s+:data-state="analysisRunState">\s*\{\{ analysisRunMessage \}\}\s*<\/p>/s);
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
