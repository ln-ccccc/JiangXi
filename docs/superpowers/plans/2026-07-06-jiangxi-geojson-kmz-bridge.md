# 江西面 GeoJSON 桥接 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `/api/geojson` 直接从 `D:\项目\江西数据\Jiangxi_NaturalMine.kmz` 输出江西面 GeoJSON，并归一化为前端地图当前可直接消费的字段结构。

**Architecture:** `miner/server.js` 继续作为 `/api/geojson` 的提供者，但不再依赖空的内存 `minesData`，而是在启动时从江西 `KMZ` 解析出面 GeoJSON，再在服务端补齐 `FID_1`、`mine_name`、`SHI`、`area`、`status_normalized` 等属性。前端只做最小兼容验证，不重写地图消费模型。

**Tech Stack:** Node.js, Express, KMZ/KML, `@mapbox/togeojson`, Vue 3, Node test, Vite build

---

## 文件结构

- Create: `miner/services/jiangxiGeoJsonSource.js`
- Create: `miner/test/jiangxiGeoJsonSource.test.js`
- Modify: `miner/server.js`
- Modify: `miner/src/composables/useMineData.js`
- Modify: `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`

---

### Task 1: 提取 KMZ 面 GeoJSON 解析器并先写失败测试

**Files:**
- Create: `miner/services/jiangxiGeoJsonSource.js`
- Create: `miner/test/jiangxiGeoJsonSource.test.js`

- [ ] **Step 1: 先写失败测试，固定解析器输出字段**

`miner/test/jiangxiGeoJsonSource.test.js`

```javascript
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { gzipSync } from 'node:zlib';

import { loadJiangxiGeoJsonFromKmz } from '../services/jiangxiGeoJsonSource.js';

function writeFakeKmz(kmlText) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'jiangxi-kmz-'));
  const kmzPath = path.join(tempDir, 'sample.kmz');
  fs.writeFileSync(kmzPath, gzipSync(Buffer.from(kmlText, 'utf8')));
  return kmzPath;
}

test('loadJiangxiGeoJsonFromKmz normalizes polygon properties', async () => {
  const kmzPath = writeFakeKmz(`<?xml version="1.0" encoding="UTF-8"?>
  <kml xmlns="http://www.opengis.net/kml/2.2">
    <Document>
      <Placemark>
        <name>江西省宜春市高安市示例矿山</name>
        <ExtendedData>
          <Data name="FID_1"><value>101</value></Data>
          <Data name="SHI"><value>宜春市</value></Data>
          <Data name="TBTYMJ"><value>15391.28</value></Data>
          <Data name="HFZLQK"><value>完全修复</value></Data>
        </ExtendedData>
        <Polygon>
          <outerBoundaryIs>
            <LinearRing>
              <coordinates>
                115.1,28.1,0 115.2,28.1,0 115.2,28.2,0 115.1,28.2,0 115.1,28.1,0
              </coordinates>
            </LinearRing>
          </outerBoundaryIs>
        </Polygon>
      </Placemark>
    </Document>
  </kml>`);

  const result = await loadJiangxiGeoJsonFromKmz(kmzPath);

  assert.equal(result.type, 'FeatureCollection');
  assert.equal(result.features.length, 1);
  assert.equal(result.features[0].geometry.type, 'Polygon');
  assert.equal(result.features[0].properties.FID_1, 101);
  assert.equal(result.features[0].properties.mine_name, '江西省宜春市高安市示例矿山');
  assert.equal(result.features[0].properties.SHI, '宜春市');
  assert.equal(result.features[0].properties.area, 15391.28);
  assert.equal(result.features[0].properties.status_normalized, 'treated');
});
```

- [ ] **Step 2: 运行测试，确认当前先失败**

Run:

```bash
cd miner
node --test test/jiangxiGeoJsonSource.test.js
```

Expected:

```text
Error [ERR_MODULE_NOT_FOUND]: Cannot find module '../services/jiangxiGeoJsonSource.js'
```

- [ ] **Step 3: 实现最小解析器**

`miner/services/jiangxiGeoJsonSource.js`

```javascript
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

import { DOMParser } from '@xmldom/xmldom';
import tj from '@mapbox/togeojson';

function normalizeStatus(value) {
  const text = String(value || '').trim();
  if (!text) return 'unknown';
  if (text.includes('完全') || text.includes('治理') || text.includes('修复')) return 'treated';
  if (text.includes('未')) return 'untreated';
  return 'unknown';
}

function pickFirstProperty(properties, keys) {
  for (const key of keys) {
    const value = properties?.[key];
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      return value;
    }
  }
  return null;
}

function toNumber(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function extractKmlTextFromKmz(kmzPath) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'jiangxi-kmz-unzip-'));
  const probe = spawnSync('powershell', [
    '-NoProfile',
    '-Command',
    `Expand-Archive -LiteralPath '${kmzPath.replace(/'/g, "''")}' -DestinationPath '${tempDir.replace(/'/g, "''")}' -Force`,
  ], { encoding: 'utf8' });
  if (probe.status !== 0) {
    throw new Error(`Expand-Archive failed: ${probe.stderr || probe.stdout}`);
  }
  const entries = fs.readdirSync(tempDir, { recursive: true });
  const kmlRelative = entries.find((item) => String(item).toLowerCase().endsWith('.kml'));
  if (!kmlRelative) {
    throw new Error(`No KML found in ${kmzPath}`);
  }
  return fs.readFileSync(path.join(tempDir, kmlRelative), 'utf8');
}

function normalizeFeature(feature, index) {
  const props = { ...(feature.properties || {}) };
  const fid = toNumber(pickFirstProperty(props, ['FID_1', 'FID', 'No', 'OBJECTID'])) ?? (index + 1);
  const mineName = String(pickFirstProperty(props, ['mine_name', 'name', '名称', '矿山位置']) || `矿山 ${fid}`);
  const city = String(pickFirstProperty(props, ['SHI', '地市', '市']) || '');
  const area = toNumber(pickFirstProperty(props, ['area', 'TBTYMJ', 'Area']));
  const rawStatus = String(pickFirstProperty(props, ['HFZLQK', '修复状态', 'status']) || '');

  return {
    ...feature,
    properties: {
      ...props,
      FID_1: fid,
      mine_name: mineName,
      SHI: city,
      area,
      HFZLQK: rawStatus,
      status_normalized: normalizeStatus(rawStatus),
    },
  };
}

export async function loadJiangxiGeoJsonFromKmz(kmzPath) {
  const kmlText = extractKmlTextFromKmz(kmzPath);
  const xml = new DOMParser().parseFromString(kmlText, 'text/xml');
  const geojson = tj.kml(xml);
  return {
    type: 'FeatureCollection',
    features: (geojson.features || [])
      .filter((feature) => feature?.geometry?.type === 'Polygon' || feature?.geometry?.type === 'MultiPolygon')
      .map((feature, index) => normalizeFeature(feature, index)),
  };
}
```

- [ ] **Step 4: 运行测试，确认解析器通过**

Run:

```bash
cd miner
node --test test/jiangxiGeoJsonSource.test.js
```

Expected:

```text
# pass 1
```

- [ ] **Step 5: Commit**

```bash
git add services/jiangxiGeoJsonSource.js test/jiangxiGeoJsonSource.test.js
git commit -m "feat: add jiangxi kmz geojson loader"
```

---

### Task 2: 把 `/api/geojson` 切到江西 KMZ 并保持旧字段兼容

**Files:**
- Modify: `miner/server.js`
- Modify: `miner/test/jiangxiGeoJsonSource.test.js`

- [ ] **Step 1: 先补 API 侧失败测试**

在 `miner/test/jiangxiGeoJsonSource.test.js` 增加字段兼容断言：

```javascript
test('loadJiangxiGeoJsonFromKmz keeps legacy map property names', async () => {
  const kmzPath = writeFakeKmz(`<?xml version="1.0" encoding="UTF-8"?>
  <kml xmlns="http://www.opengis.net/kml/2.2">
    <Document>
      <Placemark>
        <name>江西矿山A</name>
        <ExtendedData>
          <Data name="FID_1"><value>7</value></Data>
          <Data name="SHI"><value>南昌市</value></Data>
          <Data name="KCFS"><value>A</value></Data>
          <Data name="HFZLQK"><value>未治理</value></Data>
        </ExtendedData>
        <Polygon>
          <outerBoundaryIs>
            <LinearRing>
              <coordinates>
                116.1,28.6,0 116.2,28.6,0 116.2,28.7,0 116.1,28.7,0 116.1,28.6,0
              </coordinates>
            </LinearRing>
          </outerBoundaryIs>
        </Polygon>
      </Placemark>
    </Document>
  </kml>`);

  const result = await loadJiangxiGeoJsonFromKmz(kmzPath);
  const properties = result.features[0].properties;

  assert.equal(properties.FID_1, 7);
  assert.equal(properties.SHI, '南昌市');
  assert.equal(properties.KCFS, 'A');
  assert.equal(properties.status_normalized, 'untreated');
});
```

- [ ] **Step 2: 运行测试，确认当前未治理状态映射或属性透传若有问题则先暴露**

Run:

```bash
cd miner
node --test test/jiangxiGeoJsonSource.test.js
```

Expected:

```text
AssertionError for status_normalized or missing KCFS
```

- [ ] **Step 3: 接入 `server.js` 的 `/api/geojson`**

在 `miner/server.js` 添加导入：

```javascript
import { loadJiangxiGeoJsonFromKmz } from './services/jiangxiGeoJsonSource.js';
```

把 `minesData` 初始化改成基于江西 `KMZ`：

```javascript
let minesData = [];

async function loadMinesData() {
  const sourcePath = path.resolve(resolveDefaultJiangxiKmzPath(process.env.MINER_DEFAULT_KMZ_PATH));
  const geojson = await loadJiangxiGeoJsonFromKmz(sourcePath);
  minesData = geojson.features || [];
  console.log(`[Startup] loaded jiangxi geojson features=${minesData.length} source=${sourcePath}`);
}
```

在启动阶段调用：

```javascript
await loadMinesData();
```

保持 `/api/geojson` 现有返回结构不变：

```javascript
app.get('/api/geojson', authGuard, (req, res) => {
  res.json({
    type: 'FeatureCollection',
    features: minesData,
  });
});
```

- [ ] **Step 4: 运行测试并做最小接口自检**

Run:

```bash
cd miner
node --test test/jiangxiGeoJsonSource.test.js
npm run build
```

Expected:

```text
# pass 2
built in
```

- [ ] **Step 5: Commit**

```bash
git add server.js services/jiangxiGeoJsonSource.js test/jiangxiGeoJsonSource.test.js
git commit -m "feat: serve jiangxi kmz geojson from miner api"
```

---

### Task 3: 做前端最小兼容和验收报告更新

**Files:**
- Modify: `miner/src/composables/useMineData.js`
- Modify: `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`

- [ ] **Step 1: 先写前端兼容检查点**

在 `useMineData.js` 里把城市和开采方式提取逻辑扩成兼容取值：

```javascript
const city = p.SHI || p.city || p['地市'] || '';
const method = p.KCFS || p['开采方式'] || '';
```

把搜索名匹配统一成大小写兼容：

```javascript
const nameText = String(p.mine_name || p.name || '').toLowerCase();
const nameMatch = nameText.includes(q);
```

- [ ] **Step 2: 实现最小兼容修改**

`miner/src/composables/useMineData.js`

```javascript
allMinesData.value.forEach((f) => {
  const p = f.properties || {};
  const city = p.SHI || p.city || p['地市'] || '';
  const method = p.KCFS || p['开采方式'] || '';
  if (city) cities.add(city);
  if (method) methods.add(method);
});
```

```javascript
const cityMatch = !filterCity.value || (p.SHI || p.city || p['地市'] || '') === filterCity.value;
const methodMatch = !filterMethod.value || (p.KCFS || p['开采方式'] || '') === filterMethod.value;
```

```javascript
const q = searchMineId.value.toLowerCase();
const idMatch = String(p.FID_1) === q;
const nameText = String(p.mine_name || p.name || '').toLowerCase();
const nameMatch = nameText.includes(q);
```

- [ ] **Step 3: 更新验证报告，补 `/api/geojson` 面闭环验收项**

在 `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md` 追加：

```md
## 江西面 GeoJSON 补充验证

- `/api/geojson` 已改为从 `D:\项目\江西数据\Jiangxi_NaturalMine.kmz` 输出面 GeoJSON
- 返回字段已兼容 `FID_1`、`mine_name`、`SHI`、`area`、`status_normalized`
- 地图页应能基于江西面图斑执行 `fitBounds`
- 该链路补齐后，`/api/geojson` 不再返回空 `FeatureCollection`
```

- [ ] **Step 4: 运行构建与最小联调**

Run:

```bash
cd miner
npm run build
```

Then verify:

```text
1. 启动 miner API
2. 登录后请求 /api/geojson
3. 确认 features.length > 0
4. 确认 geometry.type 为 Polygon 或 MultiPolygon
5. 确认前端地图能加载江西面图斑
```

- [ ] **Step 5: Commit**

```bash
git add src/composables/useMineData.js ../docs/superpowers/reports/2026-07-05-formal-delivery-validation.md
git commit -m "feat: consume jiangxi polygon geojson in map flow"
```

---

## 自检结果

- Spec coverage: 已覆盖 KMZ 解析、`/api/geojson` 输出、前端最小兼容、报告更新与联调
- Placeholder scan: 未保留 `TBD`、`TODO`、`待定`
- Type consistency: 统一使用 `loadJiangxiGeoJsonFromKmz()`、`FID_1`、`mine_name`、`SHI`、`area`、`status_normalized`
