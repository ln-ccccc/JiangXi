import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

import { parseEcologyWorkbookRows } from '../services/ecologySeries.js';

const read = (relativePath) => readFile(new URL(relativePath, import.meta.url), 'utf8');

test('顶部栏在矿山地图视图下提供推理工作台与趋势报告入口并完成事件接线', async () => {
  const header = await read('../src/components/TheHeader.vue');
  const dashboard = await read('../src/components/MapDashboard.vue');

  // TheHeader：emit 声明 + 地图视图下的入口按钮（含 aria-label）
  assert.match(header, /defineEmits\(\[[^\]]*['"]open-inference['"][^\]]*\]/u);
  assert.match(header, /defineEmits\(\[[^\]]*['"]open-trend-report['"][^\]]*\]/u);
  assert.match(header, /\$emit\(['"]open-inference['"]\)/u);
  assert.match(header, /\$emit\(['"]open-trend-report['"]\)/u);
  assert.match(header, /aria-label="打开推理工作台"/u);
  assert.match(header, /aria-label="打开趋势报告"/u);
  assert.match(header, /v-if="currentView === 'map'"/u);

  // MapDashboard：监听入口事件并置 true，弹窗 visible 与开关变量连通
  assert.match(dashboard, /@open-inference="showInferenceModal = true"/u);
  assert.match(dashboard, /@open-trend-report="showTrendReportModal = true"/u);
  assert.match(dashboard, /:visible="showInferenceModal"/u);
  assert.match(dashboard, /:visible="showTrendReportModal"/u);
});

test('server.js 推理 execFile 必须带超时与终止信号，防止挂死永久锁死同步任务', async () => {
  const server = await read('../server.js');

  assert.match(server, /timeout:\s*90\s*\*\s*60\s*\*\s*1000/u);
  assert.match(server, /killSignal:\s*['"]SIGTERM['"]/u);
});

test('生态诊断面板 predictionItems 键集与服务端 PREDICTION_FIELDS 完全一致', async () => {
  const panel = await read('../src/components/EcologyDiagnosisPanels.vue');

  const panelKeys = [...panel.matchAll(/prediction\.value\.([A-Za-z_]+)/gu)].map(
    (match) => match[1]
  );
  assert.ok(panelKeys.length >= 9, 'predictionItems 至少应覆盖 9 个预测字段');

  const dataMap = parseEcologyWorkbookRows([{ FID: 1, TBBH: 'TBBH-1' }]);
  const backendKeys = Object.keys(Object.values(dataMap)[0].prediction);

  assert.deepEqual([...new Set(panelKeys)].sort(), [...backendKeys].sort());
});

test('推理并发防护：后端 busy 退出码以 409 透出，生态面板迟到响应丢弃（复审批次 C）', async () => {
  const server = await read('../server.js');
  const useMineData = await read('../src/composables/useMineData.js');

  // kml_roi_infer.py 跨进程推理锁占用（stdout status=busy，退出码 3）→ BFF 409 而非 500
  assert.match(server, /busyPayload\?\.status === 'busy'/u);
  assert.match(server, /res\.status\(409\)/u);
  assert.match(server, /已有一个图斑推理任务正在执行/u);

  // 生态面板请求序号守卫：快速连点图斑时旧响应不得覆盖新图斑数据
  assert.match(useMineData, /ecologyProfileRequestId/u);
  assert.match(useMineData, /requestId !== ecologyProfileRequestId/u);
});
