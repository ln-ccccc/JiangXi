# 江西 `miner` 地图与监测看板整改 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复江西 `miner` 的底图/图斑可见性，并把地图总览、右侧图表和图斑详情统一调整为江西现有真实字段口径。

**Architecture:** 先把 `miner/server.js` 中混杂的统计逻辑抽成单独的江西看板统计服务，用可测试的纯函数产出“面积口径卡片 + 数量口径分布 + 明确的错误态元数据”。前端继续复用 `useMineData()` 作为数据入口，但替换左右侧栏和详情弹窗的展示契约，让地图主区、总览卡片和分析详情分层表达。

**Tech Stack:** Node.js, Express, Vue 3, Leaflet, ECharts, node:test

---

## 文件结构

### 修改文件

- Modify: `miner/server.js`
- Modify: `miner/src/components/MapDashboard.vue`
- Modify: `miner/src/components/LeftSidebar.vue`
- Modify: `miner/src/components/RightSidebar.vue`
- Modify: `miner/src/components/MineDetailModal.vue`
- Modify: `miner/src/components/MapContainer.vue`
- Modify: `miner/src/composables/useMineData.js`
- Modify: `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`

### 新增文件

- Create: `miner/services/dashboardStats.js`
- Create: `miner/test/dashboardStats.test.js`

### 责任划分

- `miner/services/dashboardStats.js`
  - 负责把图斑 GeoJSON 转成首屏卡片、右侧分布图和筛选维度所需的结构化统计。
  - 只输出本轮确认过的真实口径：图斑总数、图斑总面积、已治理面积占比、未治理面积占比、地市分布、图斑类型分布、修复方式分布、开采方式分布。
- `miner/server.js`
  - 复用 `dashboardStats.js` 生成 `/api/stats` 响应，不再直接在路由里拼装错误口径字段。
- `useMineData.js`
  - 负责把新 `/api/stats` 响应转成页面状态，并把“统计失败”和“图斑失败”拆开。
- `LeftSidebar.vue`
  - 负责只显示 4 个基础指标、筛选器和“修复方式分布”。
- `RightSidebar.vue`
  - 负责只显示地市分布、图斑类型分布、开采方式分布，移除 `变化面积 / 覆盖率 / 修复后地类`。
- `MapContainer.vue`
  - 负责底图/图斑可见性提示、`fitBounds`、地图错误态和图斑点击事件。
- `MineDetailModal.vue`
  - 负责基础事实优先、分析结果后置，避免默认先落到 NDVI/变化矩阵。

---

### Task 1: 抽出江西看板统计服务并锁定口径

**Files:**
- Create: `miner/services/dashboardStats.js`
- Create: `miner/test/dashboardStats.test.js`
- Modify: `miner/server.js`

- [ ] **Step 1: 先补统计服务测试，锁定面积口径和分布口径**

在 `miner/test/dashboardStats.test.js` 新增以下测试：

```js
import assert from 'node:assert/strict';
import test from 'node:test';

import { buildDashboardStats } from '../services/dashboardStats.js';

test('buildDashboardStats returns Jiangxi overview metrics with area-based status ratio', () => {
  const stats = buildDashboardStats({
    minesData: [
      {
        type: 'Feature',
        properties: {
          FID_1: 1,
          SHI: '赣州市',
          area: 100,
          HFZLQK: '完全修复',
          status_normalized: 'treated',
          NXFFS: '自然恢复',
          STWT: '无主废弃矿山',
          KCFS: '露天开采',
        },
        geometry: { type: 'Polygon', coordinates: [] },
      },
      {
        type: 'Feature',
        properties: {
          FID_1: 2,
          SHI: '上饶市',
          area: 300,
          HFZLQK: '未治理',
          status_normalized: 'untreated',
          NXFFS: '工程修复',
          STWT: '历史遗留矿山',
          KCFS: '地下开采',
        },
        geometry: { type: 'Polygon', coordinates: [] },
      },
    ],
  });

  assert.equal(stats.overview.plot_total, 2);
  assert.equal(stats.overview.area_total, 400);
  assert.equal(stats.overview.treated_area, 100);
  assert.equal(stats.overview.untreated_area, 300);
  assert.equal(stats.overview.treated_area_ratio, 0.25);
  assert.equal(stats.overview.untreated_area_ratio, 0.75);
  assert.deepEqual(stats.city_distribution, [
    { name: '赣州市', value: 1 },
    { name: '上饶市', value: 1 },
  ]);
  assert.deepEqual(stats.damage_type_distribution, [
    { name: '历史遗留矿山', value: 1 },
    { name: '无主废弃矿山', value: 1 },
  ]);
  assert.deepEqual(stats.restoration_method_distribution, [
    { name: '工程修复', value: 1 },
    { name: '自然恢复', value: 1 },
  ]);
  assert.deepEqual(stats.mining_method_distribution, [
    { name: '地下开采', value: 1 },
    { name: '露天开采', value: 1 },
  ]);
});

test('buildDashboardStats keeps unknown buckets explicit and never returns fake land type stats', () => {
  const stats = buildDashboardStats({
    minesData: [
      {
        type: 'Feature',
        properties: {
          FID_1: 10,
          area: 0,
          HFZLQK: '',
          status_normalized: 'unknown',
          SHI: '',
          STWT: '',
          NXFFS: '',
          KCFS: '',
        },
        geometry: { type: 'Polygon', coordinates: [] },
      },
    ],
  });

  assert.equal(stats.overview.plot_total, 1);
  assert.equal(stats.overview.area_total, 0);
  assert.equal(stats.overview.treated_area_ratio, 0);
  assert.equal(stats.overview.untreated_area_ratio, 0);
  assert.deepEqual(stats.city_distribution, [{ name: '未标注地市', value: 1 }]);
  assert.deepEqual(stats.damage_type_distribution, [{ name: '未知图斑类型', value: 1 }]);
  assert.deepEqual(stats.restoration_method_distribution, [{ name: '未知修复方式', value: 1 }]);
  assert.deepEqual(stats.mining_method_distribution, [{ name: '未知开采方式', value: 1 }]);
  assert.equal('landTypeList' in stats, false);
  assert.equal('changeAreaStats' in stats, false);
});
```

- [ ] **Step 2: 运行测试，确认当前先失败**

Run:

```bash
cd miner
node --test test/dashboardStats.test.js
```

Expected:

```text
ERR_MODULE_NOT_FOUND
```

- [ ] **Step 3: 实现新的统计服务**

创建 `miner/services/dashboardStats.js`：

```js
function normalizeBucket(value, fallback) {
  const text = String(value || '').trim();
  return text || fallback;
}

function toFiniteNumber(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : 0;
}

function sortEntries(statsMap) {
  return Object.entries(statsMap)
    .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0], 'zh-CN'))
    .map(([name, value]) => ({ name, value }));
}

export function buildDashboardStats({ minesData = [] } = {}) {
  let areaTotal = 0;
  let treatedArea = 0;
  let untreatedArea = 0;

  const cityStats = {};
  const damageTypeStats = {};
  const restorationMethodStats = {};
  const miningMethodStats = {};

  for (const feature of minesData) {
    const p = feature?.properties || {};
    const area = toFiniteNumber(p.area || p.TBTYMJ || p.TBTYMJ_1);
    areaTotal += area;

    const status = String(p.status_normalized || '').trim().toLowerCase();
    if (status === 'treated') treatedArea += area;
    if (status === 'untreated') untreatedArea += area;

    const city = normalizeBucket(p.SHI || p.city || p['地市'], '未标注地市');
    const damageType = normalizeBucket(p.STWT, '未知图斑类型');
    const restorationMethod = normalizeBucket(p.NXFFS, '未知修复方式');
    const miningMethod = normalizeBucket(p.KCFS, '未知开采方式');

    cityStats[city] = (cityStats[city] || 0) + 1;
    damageTypeStats[damageType] = (damageTypeStats[damageType] || 0) + 1;
    restorationMethodStats[restorationMethod] = (restorationMethodStats[restorationMethod] || 0) + 1;
    miningMethodStats[miningMethod] = (miningMethodStats[miningMethod] || 0) + 1;
  }

  return {
    overview: {
      plot_total: minesData.length,
      area_total: Number(areaTotal.toFixed(2)),
      treated_area: Number(treatedArea.toFixed(2)),
      untreated_area: Number(untreatedArea.toFixed(2)),
      treated_area_ratio: areaTotal > 0 ? Number((treatedArea / areaTotal).toFixed(4)) : 0,
      untreated_area_ratio: areaTotal > 0 ? Number((untreatedArea / areaTotal).toFixed(4)) : 0,
    },
    city_distribution: sortEntries(cityStats),
    damage_type_distribution: sortEntries(damageTypeStats),
    restoration_method_distribution: sortEntries(restorationMethodStats),
    mining_method_distribution: sortEntries(miningMethodStats),
  };
}
```

- [ ] **Step 4: 让 `/api/stats` 使用新服务并移除错误字段**

在 `miner/server.js` 顶部新增导入：

```js
import { buildDashboardStats } from './services/dashboardStats.js';
```

把 `/api/stats` 路由替换为：

```js
app.get('/api/stats', authGuard, (req, res) => {
  const stats = buildDashboardStats({ minesData });
  res.json(stats);
});
```

- [ ] **Step 5: 运行测试验证新口径**

Run:

```bash
cd miner
node --test test/dashboardStats.test.js
```

Expected:

```text
ℹ pass 2
ℹ fail 0
```

- [ ] **Step 6: 记录当前环境不是 Git 仓库，跳过 commit**

Run:

```bash
cd ..
git rev-parse --is-inside-work-tree
```

Expected:

```text
fatal: not a git repository
```

---

### Task 2: 重做总览卡片与右侧图表口径

**Files:**
- Modify: `miner/src/composables/useMineData.js`
- Modify: `miner/src/components/MapDashboard.vue`
- Modify: `miner/src/components/LeftSidebar.vue`
- Modify: `miner/src/components/RightSidebar.vue`

- [ ] **Step 1: 先补前端数据映射测试**

在 `miner/test/dashboardStats.test.js` 追加：

```js
test('buildDashboardStats output shape matches dashboard contract expected by Vue panels', () => {
  const stats = buildDashboardStats({ minesData: [] });

  assert.deepEqual(Object.keys(stats), [
    'overview',
    'city_distribution',
    'damage_type_distribution',
    'restoration_method_distribution',
    'mining_method_distribution',
  ]);

  assert.deepEqual(Object.keys(stats.overview), [
    'plot_total',
    'area_total',
    'treated_area',
    'untreated_area',
    'treated_area_ratio',
    'untreated_area_ratio',
  ]);
});
```

- [ ] **Step 2: 运行测试，确认契约测试通过或随 Task 1 一并通过**

Run:

```bash
cd miner
node --test test/dashboardStats.test.js
```

Expected:

```text
ℹ pass 3
ℹ fail 0
```

- [ ] **Step 3: 改造 `useMineData.js` 的状态字段**

把 `useMineData.js` 中旧字段：

```js
const mineTotal = ref(0);
const overviewArea = ref(0);
const treatedCount = ref(0);
const untreatedCount = ref(0);
const restorationMethodList = ref([]);
const miningMethodList = ref([]);
const landTypeList = ref([]);
const changeAreaStats = ref({
  total_changed_km2: 0,
  valid_mine_count: 0,
  missing_mine_count: 0,
  coverage_ratio: 0
});
```

替换为：

```js
const plotTotal = ref(0);
const plotAreaTotal = ref(0);
const treatedArea = ref(0);
const untreatedArea = ref(0);
const treatedAreaRatio = ref(0);
const untreatedAreaRatio = ref(0);

const cityDistribution = ref([]);
const damageTypeDistribution = ref([]);
const restorationMethodDistribution = ref([]);
const miningMethodDistribution = ref([]);
```

并把 `loadData()` 中统计映射改成：

```js
const stats = statsRes.data || {};
const overview = stats.overview || {};

plotTotal.value = Number(overview.plot_total || 0);
plotAreaTotal.value = Number(overview.area_total || 0);
treatedArea.value = Number(overview.treated_area || 0);
untreatedArea.value = Number(overview.untreated_area || 0);
treatedAreaRatio.value = Number(overview.treated_area_ratio || 0);
untreatedAreaRatio.value = Number(overview.untreated_area_ratio || 0);

cityDistribution.value = stats.city_distribution || [];
damageTypeDistribution.value = stats.damage_type_distribution || [];
restorationMethodDistribution.value = stats.restoration_method_distribution || [];
miningMethodDistribution.value = stats.mining_method_distribution || [];
```

- [ ] **Step 4: 把 `MapDashboard.vue` 传参与事件收口到新契约**

把 `MapDashboard.vue` 左侧栏传参改成：

```vue
<LeftSidebar
  v-model:filterCity="filterCity"
  v-model:filterStatus="filterStatus"
  v-model:filterMethod="filterMethod"
  v-model:searchMineId="searchMineId"
  :plotTotal="plotTotal"
  :plotAreaTotal="plotAreaTotal"
  :treatedAreaRatio="treatedAreaRatio"
  :untreatedAreaRatio="untreatedAreaRatio"
  :restorationMethodDistribution="restorationMethodDistribution"
  :cityOptions="cityOptions"
  :miningMethodOptions="miningMethodOptions"
  :dataLoadError="dataLoadError"
  @apply-filters="applyFilters"
  @reset-filters="resetFilters"
  @search="performSearch"
/>
```

把右侧栏传参改成：

```vue
<RightSidebar
  :cityDistribution="cityDistribution"
  :damageTypeDistribution="damageTypeDistribution"
  :miningMethodDistribution="miningMethodDistribution"
  :dataLoadError="dataLoadError"
/>
```

并删掉：

```vue
@open-inference="showInferenceModal = true"
@open-trend-report="openTrendReport"
```

因为这些不再属于首屏左栏主操作区。

- [ ] **Step 5: 重写 `LeftSidebar.vue`**

把核心指标区替换为：

```vue
<div class="metric-grid">
  <div class="metric-card">
    <div class="metric-label">图斑总数</div>
    <div class="metric-value text-cyan">{{ plotTotal }}</div>
    <div class="metric-unit">个</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">图斑总面积</div>
    <div class="metric-value text-blue">{{ (plotAreaTotal / 10000).toFixed(2) }}</div>
    <div class="metric-unit">公顷</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">已治理面积占比</div>
    <div class="metric-value text-green">{{ (treatedAreaRatio * 100).toFixed(1) }}</div>
    <div class="metric-unit">%</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">未治理面积占比</div>
    <div class="metric-value text-yellow">{{ (untreatedAreaRatio * 100).toFixed(1) }}</div>
    <div class="metric-unit">%</div>
  </div>
</div>
```

把筛选标题和字段名改成：

```vue
<label>所属地市</label>
<option value="">全部地市</option>
```

并把底部模块改成：

```vue
<div class="ranking-panel glass-panel">
  <div class="panel-header"><h3>修复方式分布</h3></div>
  <div class="ranking-list">
    <div class="ranking-item" v-for="(item, index) in restorationMethodDistribution" :key="item.name">
      <span class="rank-num">{{ index + 1 }}</span>
      <span class="rank-name">{{ item.name }}</span>
      <div class="rank-bar-container">
        <div class="rank-bar" :style="{ width: (item.value / (restorationMethodDistribution[0]?.value || 1) * 100) + '%' }"></div>
      </div>
      <span class="rank-val">{{ item.value }}</span>
    </div>
  </div>
</div>
```

- [ ] **Step 6: 重写 `RightSidebar.vue`**

把整个模板替换成 3 张图：

```vue
<div class="chart-panel glass-panel">
  <div class="panel-header"><h3>地市图斑分布</h3></div>
  <div ref="cityChartRef" class="chart-box"></div>
</div>

<div class="chart-panel glass-panel">
  <div class="panel-header"><h3>图斑类型分布</h3></div>
  <div ref="damageTypeChartRef" class="chart-box"></div>
</div>

<div class="chart-panel glass-panel">
  <div class="panel-header"><h3>开采方式分布</h3></div>
  <div ref="miningMethodChartRef" class="chart-box"></div>
</div>
```

柱图初始化逻辑统一为：

```js
const makeBarOption = (title, list) => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: '3%', right: '4%', bottom: '3%', top: '3%', containLabel: true },
  xAxis: { type: 'value', splitLine: { show: false }, axisLabel: { color: '#ccc' } },
  yAxis: {
    type: 'category',
    data: list.map((item) => item.name),
    axisLabel: { color: '#ccc', width: 96, overflow: 'truncate' }
  },
  series: [{
    type: 'bar',
    data: list.map((item) => item.value),
    barWidth: '60%',
  }]
});
```

删除旧 props：

```js
treatedCount
untreatedCount
landTypeList
changeAreaStats
```

改为：

```js
cityDistribution: Array,
damageTypeDistribution: Array,
miningMethodDistribution: Array,
dataLoadError: String,
```

- [ ] **Step 7: 运行前端回归测试**

Run:

```bash
cd miner
node --test test/dashboardStats.test.js test/minerDefaults.test.js test/viewNavigation.test.js
```

Expected:

```text
ℹ fail 0
```

- [ ] **Step 8: 运行构建验证**

Run:

```bash
cd miner
npm run build
```

Expected:

```text
✓ built
```

---

### Task 3: 修复地图状态提示与详情面板分层

**Files:**
- Modify: `miner/src/components/MapContainer.vue`
- Modify: `miner/src/components/MineDetailModal.vue`
- Modify: `miner/src/components/MapDashboard.vue`
- Modify: `miner/src/composables/useMineData.js`

- [ ] **Step 1: 在 `MapContainer.vue` 增加底图/图斑状态提示**

新增状态条：

```vue
<div v-if="mapStatusMessage" class="map-status-banner" :class="mapStatusKind">
  {{ mapStatusMessage }}
</div>
```

新增状态变量：

```js
const mapStatusMessage = ref('');
const mapStatusKind = ref('info');
```

在底图 fallback 逻辑里追加：

```js
mapStatusKind.value = 'warning';
mapStatusMessage.value = '在线底图加载失败，已保留江西图斑';
```

在 `renderMapMarkers()` 中追加：

```js
if (!props.minesData || props.minesData.length === 0) {
  mapStatusKind.value = 'error';
  mapStatusMessage.value = '当前筛选条件下无匹配图斑';
  return;
}

if (mapStatusKind.value !== 'warning') {
  mapStatusKind.value = 'success';
  mapStatusMessage.value = '江西图斑已加载';
}
```

- [ ] **Step 2: 把图斑详情基础事实补齐到 `handleSelectMine()`**

在 `MapDashboard.vue` 中把 `selectedMine.value` 改成：

```js
selectedMine.value = {
  mine_id: properties.FID_1,
  name: properties.mine_name || properties.name || `矿山 ${properties.FID_1}`,
  city: properties.SHI || properties.city || '未标注地市',
  area: properties.area || properties.TBTYMJ || 0,
  status_raw: properties.HFZLQK || '未知',
  status_normalized: properties.status_normalized || 'unknown',
  restoration_method: properties.NXFFS || '未知修复方式',
  damage_type: properties.STWT || '未知图斑类型',
  mining_method: properties.KCFS || '未知开采方式',
  center_lat: center.lat,
  center_lng: center.lng,
};
```

- [ ] **Step 3: 重写 `MineDetailModal.vue` 的首屏信息区**

把基础信息网格改成：

```vue
<div class="info-grid">
  <div class="info-item"><span class="label">图斑ID:</span> <span class="val">{{ mineData.mine_id }}</span></div>
  <div class="info-item"><span class="label">所属地市:</span> <span class="val">{{ mineData.city || '暂无' }}</span></div>
  <div class="info-item"><span class="label">面积:</span> <span class="val">{{ mineData.area ? Number(mineData.area).toFixed(2) : '暂无' }} m²</span></div>
  <div class="info-item"><span class="label">治理状态:</span> <span class="status-tag" :class="mineData.status_normalized">{{ mineData.status_raw || '未知' }}</span></div>
  <div class="info-item"><span class="label">修复方式:</span> <span class="val">{{ mineData.restoration_method || '暂无' }}</span></div>
  <div class="info-item"><span class="label">图斑类型:</span> <span class="val">{{ mineData.damage_type || '暂无' }}</span></div>
  <div class="info-item"><span class="label">开采方式:</span> <span class="val">{{ mineData.mining_method || '暂无' }}</span></div>
  <div class="info-item"><span class="label">中心坐标:</span> <span class="val">{{ (mineData.center_lat||0).toFixed(4) }}, {{ (mineData.center_lng||0).toFixed(4) }}</span></div>
</div>
```

- [ ] **Step 4: 把详情标签页改成“基础事实优先、分析后置”**

在 `MineDetailModal.vue` 中把标签改成：

```vue
<div class="tabs">
  <button
    v-for="tab in ['基础信息', 'NDVI', 'NDBI', 'NDWI', 'NDSI', '变化矩阵', '地物分类']"
    :key="tab"
    :class="{ active: selectedTab === tab }"
    @click="$emit('tab-change', tab)"
  >
    {{ tab }}
  </button>
</div>
```

并把 `MapDashboard.vue` 默认标签改成：

```js
const selectedTab = ref('基础信息');
```

图斑点击后：

```js
selectedTab.value = '基础信息';
```

- [ ] **Step 5: 让“基础信息”成为一个明确的空分析兜底页**

在 `MineDetailModal.vue` 增加：

```vue
<template v-if="selectedTab === '基础信息'">
  <div class="fact-summary">
    当前面板优先展示江西图斑的基础业务事实；分析结果请切换到其他标签页查看。
  </div>
</template>
```

并把现有 NDVI/变化矩阵逻辑全部挂到：

```vue
<template v-else-if="selectedTab === '变化矩阵'">
```

和：

```vue
<template v-else-if="selectedTab === '地物分类'">
```

其他指数标签统一通过：

```js
const currentIndexKey = computed(() => {
  const map = {
    NDVI: 'ndvi',
    NDBI: 'ndbi',
    NDWI: 'ndwi',
    NDSI: 'ndsi',
  };
  return map[props.selectedTab] || '';
});

const currentIndexData = computed(() => props.indicesData?.[currentIndexKey.value] || null);
```

- [ ] **Step 6: 缺失分析结果时禁止再显示假 0**

把 `buildEmptyIndexEntry()` 从：

```js
mean: 0,
trend: 0,
```

改成：

```js
mean: null,
trend: null,
```

并保留：

```js
available: true,
message: '',
```

这样图表和统计框在没有数据时走 `--` 或 `暂无数据`。

- [ ] **Step 7: 运行前端回归测试与构建**

Run:

```bash
cd miner
node --test test/dashboardStats.test.js test/indexSeries.test.js test/viewNavigation.test.js
npm run build
```

Expected:

```text
ℹ fail 0
✓ built
```

---

### Task 4: 验收、浏览器复核与文档收口

**Files:**
- Modify: `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`

- [ ] **Step 1: 先在报告中追加本轮验收块**

在 `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md` 追加：

```md
## 江西 miner 看板整改补充验证（2026-07-07）

- 已修复地图页底图/图斑可见性提示
- 已将首屏卡片改为图斑总数、图斑总面积、已治理面积占比、未治理面积占比
- 已移除错误口径的“修复后地类”
- 已将“修复方式 TOP5”改为“修复方式分布”
- 已将图斑详情改为基础事实优先、分析结果后置
```

- [ ] **Step 2: 启动当前 `miner` 做最小接口验收**

Run:

```bash
cd miner
docker ps --filter "name=^geoview-jiangxi$" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected:

```text
geoview-jiangxi   Up ... (healthy)
```

若容器未运行，则按当前项目既有链路启动对应容器或开发服务后再继续。

- [ ] **Step 3: 做接口验收**

Run:

```bash
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:4000/api/auth/login -WebSession $session -ContentType 'application/json' -Body '{"username":"admin","password":"Admin@123456"}' | Out-Null
Invoke-RestMethod -Uri http://127.0.0.1:4000/api/stats -WebSession $session | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri http://127.0.0.1:4000/api/geojson -WebSession $session | ConvertTo-Json -Depth 3
```

Expected:

```text
/api/stats 中包含 overview, city_distribution, damage_type_distribution, restoration_method_distribution, mining_method_distribution
/api/geojson 返回非空 FeatureCollection
```

- [ ] **Step 4: 做浏览器验收**

Browser checklist:

```text
1. 打开 http://127.0.0.1:4000/#/map
2. 确认默认可见江西底图或明确底图失败提示
3. 确认默认可见江西图斑
4. 确认左侧卡片为图斑总数、图斑总面积、已治理面积占比、未治理面积占比
5. 确认右侧不再出现修复后地类、变化面积、覆盖率
6. 确认右侧图表为地市图斑分布、图斑类型分布、开采方式分布
7. 点击图斑后，第一屏先看到基础事实信息
```

- [ ] **Step 5: 更新报告中的最终结论**

在报告补充以下结论：

```md
- 江西地图页已恢复“有底图 + 有图斑”的可见状态
- 首屏图表已切换为江西当前真实字段口径
- 错误口径模块“修复后地类”已删除
- 图斑详情已调整为基础事实优先
```

- [ ] **Step 6: 再次确认当前目录无法 commit**

Run:

```bash
git rev-parse --is-inside-work-tree
```

Expected:

```text
fatal: not a git repository
```

---

## 自检结果

- Spec coverage: 已覆盖地图可见性修复、总览卡片重构、右侧图表整改、详情面板分层、错误态空态和验收收口。
- Placeholder scan: 未保留 `TBD`、`TODO`、`待定`、`implement later` 等占位项。
- Type consistency: 前后统一使用 `overview.plot_total / area_total / treated_area_ratio / untreated_area_ratio` 与 `city_distribution / damage_type_distribution / restoration_method_distribution / mining_method_distribution` 这一组新契约。
