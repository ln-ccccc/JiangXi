# Jiangxi Regionalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前交付包默认运行口径从云南切换为江西，并统一固化 `D:\项目\江西数据\Jiangxi_NaturalMine.kmz` 为唯一默认权威图斑源。

**Architecture:** 现有代码的前后端都已围绕 KML/KMZ 图斑和项目迁移逻辑工作，因此本次不做多省配置平台，而是在现有结构上新增一个最小的江西图斑适配层。后端与 `miner` 各自通过同名“默认江西图斑源”辅助模块读取 `Jiangxi_NaturalMine.kmz`，然后统一替换默认区域、项目名称、地图视角和测试样例。

**Tech Stack:** Python, Flask, unittest, Node.js, Express, Vue 3, Leaflet, Node test runner, KMZ/KML parsing

---

### Task 1: 固化江西图斑源适配层

**Files:**
- Create: `backend/applications/region_source/default_jiangxi_source.py`
- Create: `backend/test_default_jiangxi_source.py`
- Create: `miner/services/defaultJiangxiSource.js`
- Create: `miner/test/defaultJiangxiSource.test.js`
- Modify: `miner/server.js`

- [ ] **Step 1: 先为后端写一个失败测试，锁定默认图斑源必须是 `Jiangxi_NaturalMine.kmz`**

```python
# backend/test_default_jiangxi_source.py
import unittest
from pathlib import Path

from applications.region_source.default_jiangxi_source import (
    DEFAULT_JIANGXI_KMZ_PATH,
    resolve_default_jiangxi_kmz,
)


class TestDefaultJiangxiSource(unittest.TestCase):
    def test_default_path_points_to_authoritative_kmz(self):
        self.assertEqual(
            str(DEFAULT_JIANGXI_KMZ_PATH),
            r"D:\项目\江西数据\Jiangxi_NaturalMine.kmz",
        )

    def test_resolve_default_jiangxi_kmz_prefers_explicit_value(self):
        custom = Path(r"D:\tmp\override.kmz")
        self.assertEqual(resolve_default_jiangxi_kmz(custom), custom)
```

- [ ] **Step 2: 运行后端测试，确认当前代码里还没有这个适配模块**

Run:

```powershell
& 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend\.venv_task_20260705\Scripts\python.exe' -m unittest test_default_jiangxi_source.py -v
```

Working directory:

```text
D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend
```

Expected:
- FAIL，报 `ModuleNotFoundError: No module named 'applications.region_source.default_jiangxi_source'`

- [ ] **Step 3: 实现后端江西图斑源适配模块**

```python
# backend/applications/region_source/default_jiangxi_source.py
from pathlib import Path
from zipfile import ZipFile

DEFAULT_JIANGXI_KMZ_PATH = Path(r"D:\项目\江西数据\Jiangxi_NaturalMine.kmz")


def resolve_default_jiangxi_kmz(candidate=None) -> Path:
    if candidate:
        return Path(candidate).expanduser().resolve()
    return DEFAULT_JIANGXI_KMZ_PATH


def extract_kml_bytes_from_kmz(kmz_path: Path) -> bytes:
    with ZipFile(kmz_path, "r") as archive:
        kml_names = [name for name in archive.namelist() if name.lower().endswith(".kml")]
        if not kml_names:
            raise FileNotFoundError(f"No KML entry found in {kmz_path}")
        return archive.read(kml_names[0])
```

- [ ] **Step 4: 为 `miner` 写对应的默认图斑源测试和实现**

```js
// miner/test/defaultJiangxiSource.test.js
import assert from 'node:assert/strict';
import test from 'node:test';

import {
  DEFAULT_JIANGXI_KMZ_PATH,
  resolveDefaultJiangxiKmzPath,
} from '../services/defaultJiangxiSource.js';

test('resolveDefaultJiangxiKmzPath returns authoritative KMZ path', () => {
  assert.equal(
    DEFAULT_JIANGXI_KMZ_PATH,
    'D:/项目/江西数据/Jiangxi_NaturalMine.kmz'
  );
  assert.equal(
    resolveDefaultJiangxiKmzPath(),
    'D:/项目/江西数据/Jiangxi_NaturalMine.kmz'
  );
});
```

```js
// miner/services/defaultJiangxiSource.js
export const DEFAULT_JIANGXI_KMZ_PATH = 'D:/项目/江西数据/Jiangxi_NaturalMine.kmz';

export function resolveDefaultJiangxiKmzPath(value = '') {
  const text = String(value || '').trim();
  return text || DEFAULT_JIANGXI_KMZ_PATH;
}
```

- [ ] **Step 5: 在 `miner/server.js` 中先只替换默认图斑路径常量，并跑最小测试**

```js
// miner/server.js
import { resolveDefaultJiangxiKmzPath } from './services/defaultJiangxiSource.js';

const defaultKmlPath = resolveDefaultJiangxiKmzPath(process.env.MINER_DEFAULT_KMZ_PATH);
```

Run:

```powershell
node --test test/defaultJiangxiSource.test.js
& 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend\.venv_task_20260705\Scripts\python.exe' -m unittest test_default_jiangxi_source.py -v
```

Working directories:

```text
Miner tests: D:\项目\JiangXi\YunNan_prechange_20260703_223508\miner
Backend tests: D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend
```

Expected:
- 两个测试都 PASS

### Task 2: 替换后端默认区域与迁移口径

**Files:**
- Modify: `backend/applications/project_hub/legacy_migration.py`
- Modify: `backend/applications/interface/analysis.py`
- Modify: `backend/applications/kml_roi/service.py`
- Modify: `backend/kml_roi_infer.py`
- Modify: `backend/migrate_legacy_project_data.py`
- Modify: `backend/test_legacy_project_migration.py`
- Modify: `backend/test_project_api.py`

- [ ] **Step 1: 先把后端迁移测试改成江西口径并让它失败**

```python
# backend/test_legacy_project_migration.py
self.kml_path = self.miner_root / "Jiangxi_NaturalMine.kmz"

result = migrate_legacy_project_data(
    project_name="江西历史成果迁移项目",
    manager="admin",
    miner_root=self.miner_root,
    output_root=self.output_root,
    kml_path=self.kml_path,
    static_root=self.static_root,
)

self.assertEqual(project.region, "江西省")
```

```python
# backend/test_project_api.py
response = self.client.post(
    "/api/projects",
    json={
        "name": "江西一期监测",
        "region": "江西省",
        "manager": "张三",
        "remark": "江西一期项目",
        "monitor_start_year": 2024,
        "monitor_end_year": 2025,
    },
)
```

- [ ] **Step 2: 跑后端测试，确认当前实现仍然写着云南默认值**

Run:

```powershell
& 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend\.venv_task_20260705\Scripts\python.exe' -m unittest test_legacy_project_migration.py -v
& 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend\.venv_task_20260705\Scripts\python.exe' -m unittest test_project_api.py -v
```

Expected:
- 至少一个测试 FAIL，失败点是仍然返回 `云南省`、`历史成果迁移项目` 或依赖 `yunnan.kml`

- [ ] **Step 3: 把后端默认图斑入口和项目默认区域全部改成江西**

```python
# backend/applications/project_hub/legacy_migration.py
from applications.region_source.default_jiangxi_source import resolve_default_jiangxi_kmz

def _default_kml_path() -> Path:
    return resolve_default_jiangxi_kmz()

project = Project(
    name=project_name,
    region="江西省",
    manager=manager or "admin",
    remark=LEGACY_PROJECT_REMARK,
    status="active",
    monitor_start_year=min_year,
    monitor_end_year=max_year,
)
```

```python
# backend/applications/interface/analysis.py
from applications.region_source.default_jiangxi_source import resolve_default_jiangxi_kmz

def _default_kml_path():
    return resolve_default_jiangxi_kmz()
```

```python
# backend/applications/kml_roi/service.py
from applications.region_source.default_jiangxi_source import resolve_default_jiangxi_kmz

default_kml_path = resolve_default_jiangxi_kmz()
input_kml_path = Path(kml_path).expanduser().resolve() if kml_path else default_kml_path
```

```python
# backend/kml_roi_infer.py
from applications.region_source.default_jiangxi_source import resolve_default_jiangxi_kmz

parser.add_argument(
    "--kml",
    default=str(resolve_default_jiangxi_kmz()),
    help="KML/KMZ path",
)
```

```python
# backend/migrate_legacy_project_data.py
parser.add_argument("--project-name", default="江西历史成果迁移项目")
```

- [ ] **Step 4: 让迁移测试自己构造最小江西 KMZ 样本，而不是继续写 KML**

```python
# backend/test_legacy_project_migration.py
from zipfile import ZipFile

def _write_kmz(self):
    inner_kml = self.temp_dir + "/jiangxi_source.kml"
    Path(inner_kml).write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark><name>Mine 101</name><ExtendedData><SchemaData schemaUrl="#jiangxi">
      <SimpleData name="FID_1">101</SimpleData>
      <SimpleData name="SHI">赣州市</SimpleData>
      <SimpleData name="TBTYMJ">123.5</SimpleData>
      <SimpleData name="HFZLQK">treated</SimpleData>
    </SchemaData></ExtendedData></Placemark>
  </Document>
</kml>""",
        encoding="utf-8",
    )
    with ZipFile(self.kml_path, "w") as archive:
        archive.write(inner_kml, arcname="doc.kml")
```

- [ ] **Step 5: 重跑后端测试，确认江西默认口径稳定**

Run:

```powershell
& 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend\.venv_task_20260705\Scripts\python.exe' -m unittest test_legacy_project_migration.py -v
& 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend\.venv_task_20260705\Scripts\python.exe' -m unittest test_project_api.py -v
```

Expected:
- 两组测试 PASS
- 测试输出中不再出现 `云南省` 和 `yunnan.kml` 默认断言

### Task 3: 切换 `miner` 地图范围、标题和项目文案

**Files:**
- Modify: `miner/server.js`
- Modify: `miner/src/components/MapContainer.vue`
- Modify: `miner/src/App.vue`
- Modify: `miner/index.html`
- Modify: `miner/test/projectRoutes.test.js`

- [ ] **Step 1: 先为页面和路由补一个江西口径断言**

```js
// miner/test/projectRoutes.test.js
assert.equal(body.data.items[0].name, '江西历史成果迁移项目');
assert.equal(calls[0], { name: '江西', region: '江西省', status: 'active', monitor_year: null });
```

```vue
<!-- miner/src/components/MapContainer.vue -->
const mapProvider = (import.meta.env.VITE_MINER_MAP_PROVIDER || 'gaode').toLowerCase();
```

- [ ] **Step 2: 跑现有 Node 测试，确认当前文案和默认地图逻辑仍然不是江西版本**

Run:

```powershell
node --test test/projectRoutes.test.js
```

Working directory:

```text
D:\项目\JiangXi\YunNan_prechange_20260703_223508\miner
```

Expected:
- FAIL，返回值里仍是云南/大理示例，或断言与当前行为不一致

- [ ] **Step 3: 在 `miner/server.js` 中统一读取江西 KMZ，并把默认项目口径切换为江西**

```js
// miner/server.js
const defaultKmlPath = resolveDefaultJiangxiKmzPath(process.env.MINER_DEFAULT_KMZ_PATH);

const defaultLegacyProject = {
  name: '江西历史成果迁移项目',
  region: '江西省',
};
```

```js
// 如果当前 server.js 仍直接读文本 KML，则新增一个最小 KMZ 解包步骤
import { unzipSync } from 'node:zlib';
// 若 Node 原生能力不足，则改为调用后端现有 Python 适配模块，避免再次引入第三方 zip 依赖
```

- [ ] **Step 4: 把前端标题、地图 provider 和初始视角兜底改为江西口径**

```html
<!-- miner/index.html -->
<title>江西矿山生态修复智能监测平台</title>
```

```vue
<!-- miner/src/components/MapContainer.vue -->
const mapProvider = (import.meta.env.VITE_MINER_MAP_PROVIDER || 'gaode').toLowerCase();

map.value = L.map(mapElement.value, { zoomControl: false, attributionControl: false })
  .setView([27.6, 115.9], 7);

const fitMineLayerBounds = () => {
  if (!map.value || !mineLayer.value) return;
  const bounds = mineLayer.value.getBounds();
  if (!bounds || !bounds.isValid()) return;
  map.value.fitBounds(bounds, { paddingTopLeft: [24, 30], paddingBottomRight: [24, 30], maxZoom: 11 });
};
```

```vue
<!-- miner/src/App.vue -->
const platformTitle = '江西矿山生态修复智能监测平台';
```

- [ ] **Step 5: 重跑 `miner` 构建与 Node 测试**

Run:

```powershell
node --test test/defaultJiangxiSource.test.js
node --test test/projectRoutes.test.js
npm run build
```

Expected:
- 两个 Node 测试 PASS
- `npm run build` PASS
- 产物不再引用默认云南平台标题

### Task 4: 收口文档、测试样例和验收脚本

**Files:**
- Modify: `docs/project_summary.md`
- Modify: `docs/system_guide.md`
- Modify: `docs/offline_deployment_guide.md`
- Modify: `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`
- Modify: `docs/superpowers/specs/2026-07-05-jiangxi-regionalization-design.md`

- [ ] **Step 1: 先把验收报告里的关键结论改成江西目标断言**

```markdown
- 默认业务数据源：`D:\项目\江西数据\Jiangxi_NaturalMine.kmz`
- 工作台默认项目：江西历史成果迁移项目
- 地图筛选项：江西地市
- 在线卫星底图：gaode
```

- [ ] **Step 2: 更新交付文档里的区域说明和启动参数**

```markdown
默认图斑源：`D:\项目\江西数据\Jiangxi_NaturalMine.kmz`
默认在线底图：`MINER_MAP_PROVIDER=gaode`
默认区域口径：江西省
```

- [ ] **Step 3: 执行江西化后的完整回归验证**

Run:

```powershell
& 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend\.venv_task_20260705\Scripts\python.exe' -m unittest test_default_jiangxi_source.py -v
& 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend\.venv_task_20260705\Scripts\python.exe' -m unittest test_legacy_project_migration.py -v
& 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend\.venv_task_20260705\Scripts\python.exe' -m unittest test_project_api.py -v
node --test test/defaultJiangxiSource.test.js
node --test test/projectRoutes.test.js
npm run build
```

Working directories:

```text
Backend: D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend
Miner: D:\项目\JiangXi\YunNan_prechange_20260703_223508\miner
```

Expected:
- 所有后端测试 PASS
- 所有 Node 测试 PASS
- `npm run build` PASS

- [ ] **Step 4: 重新执行一次最小联调验收**

Run:

```powershell
$env:APP_IMAGE='geoview-runtime:split-clean'
$env:MYSQL_IMAGE='registry.openanolis.cn/openanolis/mysql:8.0.30-8.6'
$env:ADMIN_PASSWORD='Secret123!'
$env:SECRET_KEY='temporary-delivery-check-key'
$env:MINER_MAP_PROVIDER='gaode'
$env:MINER_DEFAULT_KMZ_PATH='D:\项目\江西数据\Jiangxi_NaturalMine.kmz'
docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker compose -f docker-compose.prod.yml ps
```

Expected:
- `cugrs-backend`、`cugrs-frontend`、`cugrs-miner-api`、`cugrs-miner-web`、`cugrs-mysql` 全部为 `Up`
- 后续浏览器验收时，工作台标题、项目区域和地图筛选项都应表现为江西口径

- [ ] **Step 5: 更新最终验证报告**

```markdown
# Jiangxi Regionalization Validation Addendum

- Default mine source: `D:\项目\江西数据\Jiangxi_NaturalMine.kmz`
- Backend defaults: `PASS`
- Legacy migration semantics: `PASS`
- Miner title/map defaults: `PASS`
- Jiangxi browser acceptance: `PASS` only if no 云南/大理/曲靖 strings remain in the main flow
```
