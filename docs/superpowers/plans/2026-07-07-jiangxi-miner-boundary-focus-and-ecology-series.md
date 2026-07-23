# 江西 Miner 边界聚焦与年度生态指标 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为江西 Miner 地图页补齐真实省级边界聚焦、矿山高亮描边，并把 `348图斑_TableMERNet无图像预测结果.xlsx` 中的年度生态指标接入图斑详情弹窗。

**Architecture:** 采用“静态边界文件 + 地图前端渲染 + 后端一次性加载 Excel 年度指标 + 弹窗按标签展示”的方案。地图视觉增强仅修改 `MapContainer.vue` 及相关状态文案；年度生态指标通过新的服务层解析宽表 Excel，再以单独接口供前端按 `fid` 拉取，避免把解析逻辑塞进组件。

**Tech Stack:** Vue 3, Leaflet, ECharts, Express, Node.js, xlsx, node:test, Docker

---

## 文件结构

**Create**
- `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\public\boundaries\jiangxi-province.geojson`
- `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\services\ecologySeries.js`
- `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\test\ecologySeries.test.js`

**Modify**
- `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\server.js`
- `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\src\composables\useMineData.js`
- `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\src\components\MapDashboard.vue`
- `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\src\components\MapContainer.vue`
- `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\src\components\MineDetailModal.vue`
- `d:\项目\JiangXi\YunNan_prechange_20260703_223508\docs\superpowers\reports\2026-07-05-formal-delivery-validation.md`

**职责**
- `jiangxi-province.geojson`：静态江西省一级行政区边界，供前端直接加载。
- `ecologySeries.js`：解析 Excel 宽表，提取 `NDVI / FCV / LAI / NPP / LST / SM_proxy / TVDI_proxy` 的年度序列，并计算均值、趋势、趋势判断。
- `server.js`：启动时加载年度生态指标宽表，新增生态指标接口，维持现有 `/api/mines/indices` 与 `/api/mines/change-matrix` 不受影响。
- `useMineData.js`：新增年度生态指标状态与拉取逻辑。
- `MapDashboard.vue`：点击图斑时同时触发边界聚焦和生态指标加载。
- `MapContainer.vue`：渲染江西省边界、外部遮罩、矿山高亮边界和状态文案。
- `MineDetailModal.vue`：替换旧分析标签为真实年度生态指标标签，渲染年度折线图与缺失提示。

### Task 1: 固化江西省边界静态数据

**Files:**
- Create: `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\public\boundaries\jiangxi-province.geojson`
- Modify: `d:\项目\JiangXi\YunNan_prechange_20260703_223508\docs\superpowers\reports\2026-07-05-formal-delivery-validation.md`

- [ ] **Step 1: 下载并固化江西省一级行政边界**

将公开边界数据裁剪为仅包含江西省的 GeoJSON，保存为：

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "江西省",
        "source": "public-boundary-dataset"
      },
      "geometry": {
        "type": "MultiPolygon",
        "coordinates": []
      }
    }
  ]
}
```

- [ ] **Step 2: 校验 GeoJSON 可被前端直接消费**

Run:

```bash
node -e "const fs=require('fs'); const p='d:/项目/JiangXi/YunNan_prechange_20260703_223508/miner/public/boundaries/jiangxi-province.geojson'; const data=JSON.parse(fs.readFileSync(p,'utf8')); console.log(data.type, data.features?.length, data.features?.[0]?.properties?.name)"
```

Expected:

```text
FeatureCollection 1 江西省
```

- [ ] **Step 3: 在验证报告中补充边界数据来源备注**

在报告中追加类似内容：

```md
## 江西省边界静态数据补充（2026-07-07）

- 文件：`miner/public/boundaries/jiangxi-province.geojson`
- 用途：江西省边界聚焦层与省外弱化遮罩
- 来源：公开行政区边界数据，已固化到项目内部，运行时不依赖外部接口
```

- [ ] **Step 4: 记录提交检查点**

当前工作区不是 Git 仓库，执行记录命令确认这一点：

```bash
git status
```

Expected:

```text
fatal: not a git repository
```

### Task 2: 新增 Excel 年度生态指标解析服务与接口

**Files:**
- Create: `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\services\ecologySeries.js`
- Create: `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\test\ecologySeries.test.js`
- Modify: `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\server.js`

- [ ] **Step 1: 先写服务层失败测试**

在 `ecologySeries.test.js` 中写出宽表解析与缺失值行为测试：

```js
import assert from 'node:assert/strict';
import test from 'node:test';

import {
  parseEcologyWorkbookRows,
  buildEcologySeriesPayload,
} from '../services/ecologySeries.js';

test('parseEcologyWorkbookRows extracts yearly series by metric prefix', () => {
  const rows = [
    { FID: 101, NDVI_2013: 0.1, NDVI_2014: 0.2, FCV_2013: 0.3, FCV_2014: 0.5 },
  ];
  const result = parseEcologyWorkbookRows(rows);
  assert.deepEqual(result[101].ndvi.data, [
    { year: 2013, value: 0.1 },
    { year: 2014, value: 0.2 },
  ]);
  assert.deepEqual(result[101].fcv.data, [
    { year: 2013, value: 0.3 },
    { year: 2014, value: 0.5 },
  ]);
});

test('buildEcologySeriesPayload returns missing message when mine has no yearly ecology data', () => {
  const payload = buildEcologySeriesPayload({
    fid: 999,
    dataMap: {},
  });
  assert.equal(payload.fid, 999);
  assert.equal(payload.ndvi.available, false);
  assert.match(payload.ndvi.message, /暂无该图斑年度数据/);
});
```

- [ ] **Step 2: 运行测试确认当前失败**

Run:

```bash
node --test test/ecologySeries.test.js
```

Expected:

```text
ERR_MODULE_NOT_FOUND
```

- [ ] **Step 3: 编写最小生态指标服务实现**

在 `ecologySeries.js` 中先实现宽表解析、统计计算和 payload 组装：

```js
export const ECOLOGY_METRICS = {
  ndvi: { label: 'NDVI', prefixes: ['NDVI'] },
  fcv: { label: 'FCV', prefixes: ['FCV'] },
  lai: { label: 'LAI', prefixes: ['LAI'] },
  npp: { label: 'NPP', prefixes: ['NPP'] },
  lst: { label: 'LST', prefixes: ['LST'] },
  sm_proxy: { label: '土壤湿度代理', prefixes: ['SM_proxy'] },
  tvdi_proxy: { label: '干旱指数代理', prefixes: ['TVDI_proxy'] },
};

export function calculateSeriesStats(data = []) {
  const values = data.map((item) => Number(item.value)).filter(Number.isFinite);
  if (!values.length) {
    return { mean: null, trend: null, mk_trend: '暂无' };
  }
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  if (data.length < 2) {
    return { mean: Number(mean.toFixed(3)), trend: 0, mk_trend: '稳定' };
  }
  const years = data.map((item) => Number(item.year));
  const sumX = years.reduce((a, b) => a + b, 0);
  const sumY = values.reduce((a, b) => a + b, 0);
  const sumXY = years.reduce((acc, year, index) => acc + year * values[index], 0);
  const sumXX = years.reduce((acc, year) => acc + year * year, 0);
  const denom = data.length * sumXX - sumX * sumX;
  const slope = denom !== 0 ? (data.length * sumXY - sumX * sumY) / denom : 0;
  return {
    mean: Number(mean.toFixed(3)),
    trend: Number(slope.toFixed(5)),
    mk_trend: slope > 0.0005 ? 'upward' : (slope < -0.0005 ? 'downward' : 'stable'),
  };
}

export function parseEcologyWorkbookRows(rows = []) {
  const result = {};
  for (const row of rows) {
    const fid = Number(row.FID ?? row.fid ?? row.FID_1);
    if (!Number.isFinite(fid)) continue;
    if (!result[fid]) {
      result[fid] = Object.fromEntries(
        Object.keys(ECOLOGY_METRICS).map((key) => [key, { data: [] }]),
      );
    }
    for (const [column, rawValue] of Object.entries(row)) {
      const value = Number(rawValue);
      if (!Number.isFinite(value)) continue;
      for (const [metricKey, config] of Object.entries(ECOLOGY_METRICS)) {
        const matched = config.prefixes.find((prefix) => new RegExp(`^${prefix}_(19|20)\\d{2}$`, 'i').test(column));
        if (!matched) continue;
        const year = Number(String(column).match(/(19|20)\d{2}$/)?.[0]);
        if (!Number.isFinite(year)) continue;
        result[fid][metricKey].data.push({ year, value });
      }
    }
  }
  for (const metricGroup of Object.values(result)) {
    Object.values(metricGroup).forEach((entry) => {
      entry.data.sort((a, b) => a.year - b.year);
    });
  }
  return result;
}

export function buildEcologySeriesPayload({ fid, dataMap = {} }) {
  const numericFid = Number(fid);
  const current = dataMap[numericFid] || {};
  const payload = { fid: numericFid };
  for (const [metricKey, config] of Object.entries(ECOLOGY_METRICS)) {
    const entry = current[metricKey]?.data || [];
    const stats = calculateSeriesStats(entry);
    payload[metricKey] = {
      label: config.label,
      data: entry,
      ...stats,
      available: entry.length > 0,
      message: entry.length > 0 ? '' : '暂无该图斑年度数据',
    };
  }
  return payload;
}
```

- [ ] **Step 4: 在 `server.js` 中加载 Excel 并新增接口**

在 `server.js` 中引入新服务并注册加载逻辑：

```js
import { buildEcologySeriesPayload, parseEcologyWorkbookRows } from './services/ecologySeries.js';

let ecologySeriesData = {};

function loadEcologySeriesWorkbook(filePath) {
  const fullPath = path.resolve(filePath);
  if (!fs.existsSync(fullPath)) return {};
  const workbook = xlsx.readFile(fullPath);
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = xlsx.utils.sheet_to_json(sheet, { defval: null });
  return parseEcologyWorkbookRows(rows);
}

const ecologyWorkbookPath = path.resolve(repoRoot, '..', '江西数据', '348图斑_TableMERNet无图像预测结果.xlsx');
ecologySeriesData = loadEcologySeriesWorkbook(ecologyWorkbookPath);

app.get('/api/mines/ecology-series', authGuard, (req, res) => {
  const { fid } = req.query;
  if (!fid) return res.status(400).json({ error: 'Missing FID parameter' });
  res.json(buildEcologySeriesPayload({
    fid: Number(fid),
    dataMap: ecologySeriesData,
  }));
});
```

- [ ] **Step 5: 运行测试确认通过**

Run:

```bash
node --test test/ecologySeries.test.js
```

Expected:

```text
# pass 2
```

- [ ] **Step 6: 记录提交检查点**

```bash
git status
```

Expected:

```text
fatal: not a git repository
```

### Task 3: 接入年度生态指标到前端状态与弹窗

**Files:**
- Modify: `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\src\composables\useMineData.js`
- Modify: `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\src\components\MapDashboard.vue`
- Modify: `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\src\components\MineDetailModal.vue`

- [ ] **Step 1: 先写前端状态契约草图**

在 `useMineData.js` 中定义新的空数据结构：

```js
const ECOLOGY_TAB_ORDER = [
  '基础信息',
  'NDVI',
  'FCV',
  'LAI',
  'NPP',
  'LST',
  '土壤湿度代理',
  '干旱指数代理',
  '变化矩阵',
  '地物分类',
];

const buildEmptyEcologyEntry = (label = '') => ({
  label,
  mean: null,
  trend: null,
  mk_trend: '暂无',
  data: [],
  available: false,
  message: '暂无该图斑年度数据',
});
```

- [ ] **Step 2: 实现生态指标拉取逻辑**

在 `useMineData.js` 中新增状态和请求：

```js
const mineEcologySeries = ref({
  ndvi: buildEmptyEcologyEntry('NDVI'),
  fcv: buildEmptyEcologyEntry('FCV'),
  lai: buildEmptyEcologyEntry('LAI'),
  npp: buildEmptyEcologyEntry('NPP'),
  lst: buildEmptyEcologyEntry('LST'),
  sm_proxy: buildEmptyEcologyEntry('土壤湿度代理'),
  tvdi_proxy: buildEmptyEcologyEntry('干旱指数代理'),
});

const fetchEcologySeries = async (fid) => {
  try {
    const res = await axios.get(apiUrl(`/api/mines/ecology-series?fid=${fid}`));
    mineEcologySeries.value = res.data || mineEcologySeries.value;
  } catch (_) {
    mineEcologySeries.value = {
      ndvi: buildEmptyEcologyEntry('NDVI'),
      fcv: buildEmptyEcologyEntry('FCV'),
      lai: buildEmptyEcologyEntry('LAI'),
      npp: buildEmptyEcologyEntry('NPP'),
      lst: buildEmptyEcologyEntry('LST'),
      sm_proxy: buildEmptyEcologyEntry('土壤湿度代理'),
      tvdi_proxy: buildEmptyEcologyEntry('干旱指数代理'),
    };
  }
};
```

- [ ] **Step 3: 在图斑点击后并行拉取生态指标**

在 `MapDashboard.vue` 中把点击逻辑改为：

```js
const handleMineSelect = async ({ feature, center }) => {
  const properties = feature.properties || {};
  selectedMine.value = {
    mine_id: properties.FID_1,
    name: properties.mine_name || properties.name || `图斑 ${properties.FID_1}`,
    city: properties.SHI || properties.city || '未标注地市',
    area: properties.area || properties.TBTYMJ || properties.TBTYMJ_1 || 0,
    status_raw: properties.HFZLQK || '未知',
    status_normalized: properties.status_normalized || 'unknown',
    restoration_method: properties.NXFFS || '未知修复方式',
    damage_type: properties.STWT || '未知图斑类型',
    mining_method: properties.KCFS || '未知开采方式',
    center_lat: Number.isFinite(center?.lat) ? center.lat : null,
    center_lng: Number.isFinite(center?.lng) ? center.lng : null,
  };

  await Promise.allSettled([
    fetchIndices(properties.FID_1),
    fetchEcologySeries(properties.FID_1),
  ]);

  selectedTab.value = '基础信息';
  showMineDetail.value = true;
};
```

- [ ] **Step 4: 用真实标签替换弹窗分析标签**

在 `MineDetailModal.vue` 中替换标签、映射和图表颜色：

```js
const ECOLOGY_TABS = ['基础信息', 'NDVI', 'FCV', 'LAI', 'NPP', 'LST', '土壤湿度代理', '干旱指数代理', '变化矩阵', '地物分类'];

const currentIndexKey = computed(() => {
  const map = {
    NDVI: 'ndvi',
    FCV: 'fcv',
    LAI: 'lai',
    NPP: 'npp',
    LST: 'lst',
    土壤湿度代理: 'sm_proxy',
    干旱指数代理: 'tvdi_proxy',
  };
  return map[props.selectedTab] || '';
});

const colorMap = {
  ndvi: '#00d2d3',
  fcv: '#4ecdc4',
  lai: '#55efc4',
  npp: '#81ecec',
  lst: '#ff9f43',
  sm_proxy: '#74b9ff',
  tvdi_proxy: '#a29bfe',
};
```

模板替换为：

```vue
<div class="tabs">
  <button
    v-for="tab in ECOLOGY_TABS"
    :key="tab"
    :class="{ active: selectedTab === tab }"
    @click="$emit('tab-change', tab)"
  >
    {{ tab }}
  </button>
</div>
```

- [ ] **Step 5: 补充缺失态与起止年份显示**

在趋势卡片里新增起止年份：

```vue
<div class="stat-box">
  <span class="label">年份范围</span>
  <span class="val">{{ getYearRangeText(currentIndexData?.data) }}</span>
</div>
```

并实现：

```js
const getYearRangeText = (data = []) => {
  if (!Array.isArray(data) || !data.length) return '暂无';
  return `${data[0].year} - ${data[data.length - 1].year}`;
};
```

- [ ] **Step 6: 前端构建验证**

Run:

```bash
npm run build
```

Expected:

```text
✓ built in
```

- [ ] **Step 7: 记录提交检查点**

```bash
git status
```

Expected:

```text
fatal: not a git repository
```

### Task 4: 实现江西省边界聚焦层与矿山高亮描边

**Files:**
- Modify: `d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner\src\components\MapContainer.vue`

- [ ] **Step 1: 添加江西边界层与遮罩层状态**

在 `MapContainer.vue` 中补充状态：

```js
const jiangxiBoundaryLayer = ref(null);
const jiangxiMaskLayer = ref(null);
const boundaryLoadState = ref({
  loaded: false,
  failed: false,
  message: '',
});
```

- [ ] **Step 2: 增加边界加载函数**

新增静态边界加载逻辑：

```js
const loadJiangxiBoundary = async () => {
  try {
    const res = await fetch('/boundaries/jiangxi-province.geojson');
    if (!res.ok) throw new Error('boundary_fetch_failed');
    return await res.json();
  } catch (error) {
    boundaryLoadState.value = {
      loaded: false,
      failed: true,
      message: '江西省边界加载失败，已回退到图斑范围聚焦',
    };
    return null;
  }
};
```

- [ ] **Step 3: 渲染省界轮廓和省外遮罩**

把边界渲染成两个图层：

```js
const renderBoundaryOverlay = (geojson) => {
  if (!map.value || !geojson) return;

  const worldRing = [[
    [-90, -180],
    [-90, 180],
    [90, 180],
    [90, -180],
    [-90, -180],
  ]];

  jiangxiBoundaryLayer.value = L.geoJSON(geojson, {
    style: {
      color: '#39d0ff',
      weight: 3,
      opacity: 0.95,
      fillOpacity: 0,
    },
  }).addTo(map.value);

  const provinceCoords = geojson.features?.[0]?.geometry?.coordinates || [];
  jiangxiMaskLayer.value = L.polygon([worldRing[0], ...provinceCoords[0]], {
    stroke: false,
    fillColor: '#040b14',
    fillOpacity: 0.42,
    fillRule: 'evenodd',
    interactive: false,
  }).addTo(map.value);
};
```

- [ ] **Step 4: 按省界优先聚焦，并增强矿山描边**

把矿山默认样式改为“填充弱化、边界强化”：

```js
const getMineStyle = (feature) => {
  const status = feature.properties.status_normalized || 'unknown';
  if (status === 'treated') {
    return { color: '#22e6b9', weight: 2.6, opacity: 1, fillColor: '#22e6b9', fillOpacity: 0.22 };
  }
  if (status === 'untreated') {
    return { color: '#ff8a5b', weight: 2.6, opacity: 1, fillColor: '#ff8a5b', fillOpacity: 0.22 };
  }
  return { color: '#74b9ff', weight: 2.4, opacity: 0.98, fillColor: '#74b9ff', fillOpacity: 0.18 };
};
```

首次聚焦逻辑改为：

```js
const fitBoundaryBounds = () => {
  if (!map.value || !jiangxiBoundaryLayer.value) return false;
  const bounds = jiangxiBoundaryLayer.value.getBounds();
  if (!bounds.isValid()) return false;
  map.value.fitBounds(bounds, { paddingTopLeft: [36, 40], paddingBottomRight: [36, 40], maxZoom: 9 });
  return true;
};
```

- [ ] **Step 5: 补地图状态文案与图例**

更新成功态和失败态：

```js
if (boundaryLoadState.value.loaded) {
  mapStatusKind.value = 'success';
  mapStatusMessage.value = `江西省边界与图斑已加载，共 ${props.minesData.length} 个图斑`;
}
if (boundaryLoadState.value.failed) {
  mapStatusKind.value = 'warning';
  mapStatusMessage.value = boundaryLoadState.value.message;
}
```

图例增加“江西省边界”和“省外弱化区域”说明：

```vue
<div class="legend-item"><span class="line province"></span> 江西省边界</div>
<div class="legend-item"><span class="mask"></span> 省外弱化区域</div>
```

- [ ] **Step 6: 前端构建验证**

Run:

```bash
npm run build
```

Expected:

```text
✓ built in
```

- [ ] **Step 7: 记录提交检查点**

```bash
git status
```

Expected:

```text
fatal: not a git repository
```

### Task 5: 全链路验证与单镜像复核

**Files:**
- Modify: `d:\项目\JiangXi\YunNan_prechange_20260703_223508\docs\superpowers\reports\2026-07-05-formal-delivery-validation.md`

- [ ] **Step 1: 运行后端与服务层测试**

Run:

```bash
cd d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner
node --test test/dashboardStats.test.js test/ecologySeries.test.js
```

Expected:

```text
# pass
```

- [ ] **Step 2: 重新构建前端**

Run:

```bash
cd d:\项目\JiangXi\YunNan_prechange_20260703_223508\miner
npm run build
```

Expected:

```text
✓ built in
```

- [ ] **Step 3: 重建单镜像**

Run:

```bash
cd d:\项目\JiangXi\YunNan_prechange_20260703_223508
docker build -f docker/standalone/Dockerfile.jiangxi -t geoview-jiangxi:standalone .
```

Expected:

```text
Successfully tagged geoview-jiangxi:standalone
```

- [ ] **Step 4: 重启容器并确认状态**

Run:

```bash
docker rm -f geoview-jiangxi
docker run -d --name geoview-jiangxi -p 4000:4000 -p 5008:5008 geoview-jiangxi:standalone
docker ps --filter "name=geoview-jiangxi" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected:

```text
geoview-jiangxi   Up ...   0.0.0.0:4000->4000/tcp, 0.0.0.0:5008->5008/tcp
```

- [ ] **Step 5: 浏览器人工验收**

验收清单：

```md
- 打开 `http://127.0.0.1:4000/#/map`
- 确认能看到江西省边界轮廓
- 确认省外区域被弱化
- 确认矿山图斑边界明显高于当前版本
- 点击一个图斑，确认弹窗标签包含 `NDVI / FCV / LAI / NPP / LST / 土壤湿度代理 / 干旱指数代理`
- 切换到任一年度生态指标标签，确认存在折线图、均值、年份范围
- 对一个无匹配数据图斑，确认显示“暂无该图斑年度数据”
```

- [ ] **Step 6: 更新正式验证报告**

在 `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md` 中补充：

```md
## 江西省边界聚焦与年度生态指标补充验证（2026-07-07）

- 江西省静态边界文件已接入：`miner/public/boundaries/jiangxi-province.geojson`
- 地图页已展示江西省轮廓线与省外弱化遮罩
- 矿山图斑边界已增强为高亮描边
- 弹窗已接入年度生态指标：NDVI、FCV、LAI、NPP、LST、土壤湿度代理、干旱指数代理
- 单镜像 `geoview-jiangxi:standalone` 重建后运行正常
```

- [ ] **Step 7: 记录提交检查点**

```bash
git status
```

Expected:

```text
fatal: not a git repository
```

## 自检结果

- **Spec 覆盖性：** 地图边界、聚焦遮罩、矿山高亮、Excel 年度生态指标、错误态、单镜像验证都已映射到任务 1-5。
- **占位符扫描：** 已避免使用 TBD/TODO，所有任务都给出明确文件、代码片段和命令。
- **命名一致性：** 统一采用 `ecology-series` 接口、`mineEcologySeries` 前端状态、`jiangxi-province.geojson` 边界文件名，避免任务间名称漂移。
