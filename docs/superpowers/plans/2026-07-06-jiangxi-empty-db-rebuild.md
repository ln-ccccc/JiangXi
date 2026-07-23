# 江西空库重建与首批展示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清空当前运行库中的云南历史项目与分析数据，并用 `D:\项目\江西数据\Mine.csv` 重建江西默认项目、主体矿山列表和图斑明细展示闭环。

**Architecture:** 后端新增一个“江西空库重建”导入服务，负责清库、读取 `Mine.csv`、按 `主体编号` 聚合主体、写入江西默认项目和图斑明细。前端继续复用现有项目工作台，但把绑定矿山区域升级为“主体列表 + 图斑明细下钻”，最终通过现有项目 API 返回江西数据。

**Tech Stack:** Python, Flask, SQLAlchemy, Marshmallow, Vue 3, Axios, Node test, Python unittest, Docker Compose

---

## 文件结构

### 后端

- Create: `backend/applications/models/jiangxi_seed.py`
- Create: `backend/applications/project_hub/jiangxi_seed_service.py`
- Create: `backend/seed_jiangxi_from_csv.py`
- Create: `backend/test_jiangxi_seed_service.py`
- Modify: `backend/applications/models/__init__.py`
- Modify: `backend/applications/schemas/project.py`
- Modify: `backend/applications/project_hub/service.py`
- Modify: `backend/test_project_api.py`

### 前端

- Modify: `miner/src/components/ProjectWorkspace.vue`
- Modify: `miner/src/projectWorkspace/projectWorkspaceHelpers.js`
- Modify: `miner/test/projectWorkspaceHelpers.test.js`

### 文档

- Modify: `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`

---

### Task 1: 建立江西导入数据模型与失败测试

**Files:**
- Create: `backend/applications/models/jiangxi_seed.py`
- Modify: `backend/applications/models/__init__.py`
- Modify: `backend/applications/schemas/project.py`
- Create: `backend/test_jiangxi_seed_service.py`

- [ ] **Step 1: 先写失败测试，固定聚合和清库后的目标输出**

```python
import csv
import tempfile
import unittest
from pathlib import Path

from app import create_app
from applications.extensions import db
from applications.models.analysis import Analysis
from applications.models.project import Project
from applications.project_hub.jiangxi_seed_service import (
    aggregate_subject_rows,
    reset_project_domain_tables,
)


CSV_HEADER = [
    "Lon", "Lat", "No", "省市", "地市", "区县", "矿山位置", "主体编号", "图斑编号",
    "修复图斑编号", "中心经度", "中心纬度", "Area", "图斑小类", "修复状态", "修复模式",
    "完成时间", "Area2", "未治理面积", "填报单位", "填报人", "填报日期", "备注", "矿种",
    "开采方式", "关闭年度", "图斑属性",
]


class JiangxiSeedServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _write_csv(self):
        temp_dir = Path(tempfile.mkdtemp(prefix="jiangxi_seed_"))
        csv_path = temp_dir / "Mine.csv"
        rows = [
            ["115.1", "28.1", "1", "江西省", "宜春市", "高安市", "江西省宜春市高安市村A", "SUBJECT-1", "PLOT-1", "PLOT-1", "115.1", "28.1", "100", "政策性关闭矿山", "完全修复", "自然恢复", "Dec-24", "100", "0", "高安市自然资源局", "甲", "2024-12-31", "", "84412", "A", "2017", "1"],
            ["115.2", "28.2", "2", "江西省", "宜春市", "高安市", "江西省宜春市高安市村A", "SUBJECT-1", "PLOT-2", "PLOT-2", "115.2", "28.2", "50", "政策性关闭矿山", "部分修复", "自然恢复", "Dec-24", "45", "5", "高安市自然资源局", "甲", "2025-01-01", "", "84412", "A", "2017", "4"],
            ["116.3", "28.3", "3", "江西省", "南昌市", "进贤县", "江西省南昌市进贤县村B", "SUBJECT-2", "PLOT-3", "PLOT-3", "116.3", "28.3", "80", "无主废弃矿山", "完全修复", "自然恢复", "Dec-23", "80", "0", "进贤县自然资源局", "乙", "2024-01-06", "", "84412", "A", "2018", "1"],
        ]
        with csv_path.open("w", encoding="gbk", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(CSV_HEADER)
            writer.writerows(rows)
        return csv_path

    def test_aggregate_subject_rows_groups_by_subject_code(self):
        csv_path = self._write_csv()
        subjects, skipped = aggregate_subject_rows(csv_path)

        self.assertEqual(skipped, 0)
        self.assertEqual(len(subjects), 2)
        self.assertEqual(subjects[0]["subject_code"], "SUBJECT-1")
        self.assertEqual(subjects[0]["plot_count"], 2)
        self.assertEqual(subjects[0]["area_total"], 150.0)
        self.assertEqual(subjects[0]["untreated_area_total"], 5.0)
        self.assertEqual(subjects[0]["city"], "宜春市")
        self.assertEqual(len(subjects[0]["plots"]), 2)

    def test_reset_project_domain_tables_clears_project_and_analysis_rows(self):
        db.session.add(Project(name="云南项目", region="云南省", status="active"))
        db.session.add(Analysis(type=1, before_img="a.png"))
        db.session.commit()

        reset_project_domain_tables()

        self.assertEqual(Project.query.count(), 0)
        self.assertEqual(Analysis.query.count(), 0)
```

- [ ] **Step 2: 运行测试，确认它们先失败**

Run:

```bash
cd backend
python -m unittest test_jiangxi_seed_service.py -v
```

Expected:

```text
ImportError: cannot import name 'aggregate_subject_rows'
```

- [ ] **Step 3: 建立新表模型、schema 字段和模型注册**

`backend/applications/models/jiangxi_seed.py`

```python
import datetime

from applications.extensions import db


class JiangxiMinePlot(db.Model):
    __tablename__ = "jiangxi_mine_plot"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False, index=True)
    mine_fid = db.Column(db.Integer, nullable=False, index=True)
    subject_code = db.Column(db.String(128), nullable=False, index=True)
    city = db.Column(db.String(255))
    county = db.Column(db.String(255))
    location_text = db.Column(db.String(1024))
    plot_code = db.Column(db.String(128), nullable=False, index=True)
    restored_plot_code = db.Column(db.String(128))
    plot_category = db.Column(db.String(255))
    repair_status = db.Column(db.String(255))
    repair_mode = db.Column(db.String(255))
    completed_at = db.Column(db.String(64))
    area = db.Column(db.Float)
    untreated_area = db.Column(db.Float)
    center_lng = db.Column(db.Float)
    center_lat = db.Column(db.Float)
    closed_year = db.Column(db.String(64))
    plot_attr = db.Column(db.String(64))
    create_time = db.Column(db.DateTime, default=datetime.datetime.now, nullable=False)
    update_time = db.Column(
        db.DateTime,
        default=datetime.datetime.now,
        onupdate=datetime.datetime.now,
        nullable=False,
    )
```

`backend/applications/models/__init__.py`

```python
from .analysis import Analysis
from .admin_user import AdminUser
from .jiangxi_seed import JiangxiMinePlot
from .photo import Photo
from .project import (
    Project,
    ProjectActivityLog,
    ProjectBackupRecord,
    ProjectDataset,
    ProjectExportRecord,
    ProjectMineBinding,
)
```

`backend/applications/schemas/project.py`

```python
class JiangxiMinePlotSchema(ma.Schema):
    id = fields.Integer()
    project_id = fields.Integer()
    mine_fid = fields.Integer()
    subject_code = fields.Str()
    city = fields.Str(allow_none=True)
    county = fields.Str(allow_none=True)
    location_text = fields.Str(allow_none=True)
    plot_code = fields.Str()
    restored_plot_code = fields.Str(allow_none=True)
    plot_category = fields.Str(allow_none=True)
    repair_status = fields.Str(allow_none=True)
    repair_mode = fields.Str(allow_none=True)
    completed_at = fields.Str(allow_none=True)
    area = fields.Float(allow_none=True)
    untreated_area = fields.Float(allow_none=True)
    center_lng = fields.Float(allow_none=True)
    center_lat = fields.Float(allow_none=True)
    closed_year = fields.Str(allow_none=True)
    plot_attr = fields.Str(allow_none=True)
    create_time = fields.DateTime()
    update_time = fields.DateTime()
```

- [ ] **Step 4: 运行测试，确认仍只因服务未实现而失败**

Run:

```bash
cd backend
python -m unittest test_jiangxi_seed_service.py -v
```

Expected:

```text
ImportError: cannot import name 'aggregate_subject_rows' from applications.project_hub.jiangxi_seed_service
```

- [ ] **Step 5: Commit**

```bash
git add backend/applications/models/jiangxi_seed.py backend/applications/models/__init__.py backend/applications/schemas/project.py backend/test_jiangxi_seed_service.py
git commit -m "feat: add jiangxi seed data model scaffolding"
```

---

### Task 2: 实现清库与 `Mine.csv` 导入服务

**Files:**
- Create: `backend/applications/project_hub/jiangxi_seed_service.py`
- Create: `backend/seed_jiangxi_from_csv.py`
- Create: `backend/test_jiangxi_seed_service.py`
- Modify: `backend/applications/project_hub/service.py`

- [ ] **Step 1: 扩充失败测试，固定默认项目、主体绑定和图斑明细结果**

`backend/test_jiangxi_seed_service.py`

```python
from applications.models.jiangxi_seed import JiangxiMinePlot
from applications.models.project import ProjectMineBinding
from applications.project_hub.jiangxi_seed_service import seed_jiangxi_project_from_csv

    def test_seed_jiangxi_project_from_csv_creates_default_project_bindings_and_plots(self):
        csv_path = self._write_csv()

        result = seed_jiangxi_project_from_csv(csv_path, actor="system")

        self.assertEqual(result["project_name"], "江西矿山生态修复监测项目")
        self.assertEqual(result["project_count"], 1)
        self.assertEqual(result["subject_count"], 2)
        self.assertEqual(result["plot_count"], 3)
        self.assertEqual(Project.query.count(), 1)
        self.assertEqual(ProjectMineBinding.query.count(), 2)
        self.assertEqual(JiangxiMinePlot.query.count(), 3)
        first_binding = ProjectMineBinding.query.order_by(ProjectMineBinding.mine_fid.asc()).first()
        self.assertEqual(first_binding.city_snapshot, "宜春市")
        self.assertEqual(round(first_binding.area_snapshot, 2), 150.0)
        self.assertIn("部分修复", first_binding.status_snapshot)
```

- [ ] **Step 2: 运行测试，确认服务行为尚未实现**

Run:

```bash
cd backend
python -m unittest test_jiangxi_seed_service.py -v
```

Expected:

```text
FAIL: test_seed_jiangxi_project_from_csv_creates_default_project_bindings_and_plots
AttributeError: module has no attribute 'seed_jiangxi_project_from_csv'
```

- [ ] **Step 3: 实现导入服务、清库逻辑和 CLI 入口**

`backend/applications/project_hub/jiangxi_seed_service.py`

```python
import csv
from collections import defaultdict
from pathlib import Path

from applications.extensions import db
from applications.models.analysis import Analysis
from applications.models.jiangxi_seed import JiangxiMinePlot
from applications.models.project import (
    Project,
    ProjectActivityLog,
    ProjectBackupRecord,
    ProjectDataset,
    ProjectExportRecord,
    ProjectMineBinding,
)


DEFAULT_JIANGXI_PROJECT_NAME = "江西矿山生态修复监测项目"
DEFAULT_JIANGXI_REGION = "江西省"
DEFAULT_JIANGXI_REMARK = "system_seed:jiangxi_mine_csv"


def _to_float(value):
    text = str(value or "").strip()
    return float(text) if text else 0.0


def _load_csv_rows(csv_path):
    path = Path(csv_path).expanduser().resolve()
    with path.open("r", encoding="gbk", newline="") as fp:
        return list(csv.DictReader(fp))


def reset_project_domain_tables():
    db.session.query(JiangxiMinePlot).delete()
    db.session.query(ProjectBackupRecord).delete()
    db.session.query(ProjectExportRecord).delete()
    db.session.query(ProjectActivityLog).delete()
    db.session.query(ProjectDataset).delete()
    db.session.query(ProjectMineBinding).delete()
    db.session.query(Project).delete()
    db.session.query(Analysis).delete()
    db.session.commit()


def aggregate_subject_rows(csv_path):
    grouped = defaultdict(list)
    skipped = 0
    for row in _load_csv_rows(csv_path):
        subject_code = str(row.get("主体编号") or "").strip()
        if not subject_code:
            skipped += 1
            continue
        grouped[subject_code].append(row)

    subjects = []
    for offset, subject_code in enumerate(sorted(grouped.keys()), start=1):
        rows = grouped[subject_code]
        city = str(rows[0].get("地市") or "").strip() or None
        county = str(rows[0].get("区县") or "").strip() or None
        location_text = str(rows[0].get("矿山位置") or "").strip() or None
        plots = []
        statuses = []
        for row in rows:
            plots.append(
                {
                    "plot_code": str(row.get("图斑编号") or "").strip(),
                    "restored_plot_code": str(row.get("修复图斑编号") or "").strip() or None,
                    "plot_category": str(row.get("图斑小类") or "").strip() or None,
                    "repair_status": str(row.get("修复状态") or "").strip() or None,
                    "repair_mode": str(row.get("修复模式") or "").strip() or None,
                    "completed_at": str(row.get("完成时间") or "").strip() or None,
                    "area": _to_float(row.get("Area")),
                    "untreated_area": _to_float(row.get("未治理面积")),
                    "center_lng": _to_float(row.get("中心经度") or row.get("Lon")),
                    "center_lat": _to_float(row.get("中心纬度") or row.get("Lat")),
                    "closed_year": str(row.get("关闭年度") or "").strip() or None,
                    "plot_attr": str(row.get("图斑属性") or "").strip() or None,
                    "city": city,
                    "county": county,
                    "location_text": location_text,
                }
            )
            if plots[-1]["repair_status"]:
                statuses.append(plots[-1]["repair_status"])

        subjects.append(
            {
                "mine_fid": offset,
                "subject_code": subject_code,
                "city": city,
                "county": county,
                "location_text": location_text,
                "plot_count": len(plots),
                "area_total": sum(item["area"] for item in plots),
                "untreated_area_total": sum(item["untreated_area"] for item in plots),
                "status_summary": " / ".join(sorted(set(statuses))) if statuses else None,
                "plots": plots,
            }
        )
    return subjects, skipped


def seed_jiangxi_project_from_csv(csv_path, actor="system"):
    reset_project_domain_tables()
    subjects, skipped = aggregate_subject_rows(csv_path)
    project = Project(
        name=DEFAULT_JIANGXI_PROJECT_NAME,
        region=DEFAULT_JIANGXI_REGION,
        manager="admin",
        remark=DEFAULT_JIANGXI_REMARK,
        status="active",
        monitor_start_year=2017,
        monitor_end_year=2025,
    )
    db.session.add(project)
    db.session.flush()

    for subject in subjects:
        db.session.add(
            ProjectMineBinding(
                project_id=project.id,
                mine_fid=subject["mine_fid"],
                mine_name_snapshot=subject["location_text"],
                city_snapshot=subject["city"],
                area_snapshot=subject["area_total"],
                status_snapshot=subject["status_summary"],
                sort_order=subject["mine_fid"],
            )
        )
        for plot in subject["plots"]:
            db.session.add(
                JiangxiMinePlot(
                    project_id=project.id,
                    mine_fid=subject["mine_fid"],
                    subject_code=subject["subject_code"],
                    city=plot["city"],
                    county=plot["county"],
                    location_text=plot["location_text"],
                    plot_code=plot["plot_code"],
                    restored_plot_code=plot["restored_plot_code"],
                    plot_category=plot["plot_category"],
                    repair_status=plot["repair_status"],
                    repair_mode=plot["repair_mode"],
                    completed_at=plot["completed_at"],
                    area=plot["area"],
                    untreated_area=plot["untreated_area"],
                    center_lng=plot["center_lng"],
                    center_lat=plot["center_lat"],
                    closed_year=plot["closed_year"],
                    plot_attr=plot["plot_attr"],
                )
            )

    db.session.add(
        ProjectActivityLog(
            project_id=project.id,
            event_type="jiangxi_seed_completed",
            actor=actor,
            payload_json='{"source":"Mine.csv"}',
        )
    )
    db.session.commit()
    return {
        "project_id": project.id,
        "project_name": project.name,
        "project_count": 1,
        "subject_count": len(subjects),
        "plot_count": sum(subject["plot_count"] for subject in subjects),
        "skipped_count": skipped,
    }
```

`backend/seed_jiangxi_from_csv.py`

```python
from pathlib import Path

from app import create_app
from applications.project_hub.jiangxi_seed_service import seed_jiangxi_project_from_csv


def main():
    app = create_app("production")
    csv_path = Path(r"D:\项目\江西数据\Mine.csv")
    with app.app_context():
        result = seed_jiangxi_project_from_csv(csv_path, actor="cli")
    print(result)


if __name__ == "__main__":
    main()
```

`backend/applications/project_hub/service.py`

```python
from applications.models.jiangxi_seed import JiangxiMinePlot
from applications.schemas.project import JiangxiMinePlotSchema


def get_project_detail(project_id):
    project = _get_project_or_404(project_id)
    plot_rows = JiangxiMinePlot.query.filter_by(project_id=project.id).order_by(
        JiangxiMinePlot.mine_fid.asc(),
        JiangxiMinePlot.plot_code.asc(),
    ).all()
    return {
        "summary": _serialize_summary(project),
        "mines": ProjectMineBindingSchema(many=True).dump(project.mines),
        "datasets": ProjectDatasetSchema(many=True).dump(project.datasets),
        "recent_activity": ProjectActivityLogSchema(many=True).dump(project.activities[:20]),
        "timeline": get_project_timeline(project_id)["items"],
        "exports": ProjectExportRecordSchema(many=True).dump(project.exports),
        "backups": ProjectBackupRecordSchema(many=True).dump(project.backups),
        "plots": JiangxiMinePlotSchema(many=True).dump(plot_rows),
    }
```

- [ ] **Step 4: 运行后端测试，验证导入服务和项目详情输出**

Run:

```bash
cd backend
python -m unittest test_jiangxi_seed_service.py test_project_api.py -v
```

Expected:

```text
OK
```

- [ ] **Step 5: Commit**

```bash
git add backend/applications/project_hub/jiangxi_seed_service.py backend/seed_jiangxi_from_csv.py backend/applications/project_hub/service.py backend/test_jiangxi_seed_service.py
git commit -m "feat: add jiangxi empty-db seed service"
```

---

### Task 3: 让项目 API 与工作台消费江西主体和图斑明细

**Files:**
- Modify: `backend/test_project_api.py`
- Modify: `miner/src/components/ProjectWorkspace.vue`
- Modify: `miner/src/projectWorkspace/projectWorkspaceHelpers.js`
- Modify: `miner/test/projectWorkspaceHelpers.test.js`

- [ ] **Step 1: 先补前后端失败测试，固定江西工作台显示结构**

`backend/test_project_api.py`

```python
    def test_project_detail_contains_jiangxi_plot_rows(self):
        from applications.project_hub.jiangxi_seed_service import seed_jiangxi_project_from_csv

        csv_path = self._build_minimal_jiangxi_csv()
        seed_jiangxi_project_from_csv(csv_path, actor="test")

        response = self.client.get("/api/projects")
        project_id = response.get_json()["data"]["items"][0]["id"]
        detail = self.client.get(f"/api/projects/{project_id}").get_json()["data"]

        self.assertEqual(detail["summary"]["region"], "江西省")
        self.assertGreaterEqual(len(detail["mines"]), 1)
        self.assertGreaterEqual(len(detail["plots"]), 1)
        self.assertEqual(detail["plots"][0]["subject_code"], "SUBJECT-1")
```

`miner/test/projectWorkspaceHelpers.test.js`

```javascript
import { buildMineSelectionSet, filterProjects, groupPlotsByMineFid } from '../src/projectWorkspace/projectWorkspaceHelpers.js';

test('groupPlotsByMineFid groups jiangxi plot rows under one subject', () => {
  const grouped = groupPlotsByMineFid([
    { mine_fid: 1, plot_code: 'PLOT-1', repair_status: '完全修复' },
    { mine_fid: 1, plot_code: 'PLOT-2', repair_status: '部分修复' },
    { mine_fid: 2, plot_code: 'PLOT-3', repair_status: '完全修复' },
  ]);

  assert.equal(grouped.get(1).length, 2);
  assert.equal(grouped.get(2).length, 1);
});
```

- [ ] **Step 2: 运行测试，确认前端 helper 和 API 都还未满足新结构**

Run:

```bash
cd backend
python -m unittest test_project_api.py -v
cd ..\miner
node --test test/projectWorkspaceHelpers.test.js
```

Expected:

```text
AttributeError or AssertionError about missing plots
ReferenceError: groupPlotsByMineFid is not defined
```

- [ ] **Step 3: 实现工作台明细分组和江西主体展示**

`miner/src/projectWorkspace/projectWorkspaceHelpers.js`

```javascript
export function filterProjects(items, filters = {}) {
  return (items || []).filter((item) => {
    const nameMatch = !filters.name || String(item.name || '').includes(filters.name);
    const regionMatch = !filters.region || String(item.region || '').includes(filters.region);
    const statusMatch = !filters.status || item.status === filters.status;
    const year = Number(filters.monitorYear || 0);
    const yearMatch = !year || (
      Number(item.monitor_start_year || 0) <= year &&
      Number(item.monitor_end_year || 9999) >= year
    );
    return nameMatch && regionMatch && statusMatch && yearMatch;
  });
}

export function buildMineSelectionSet(detail) {
  return new Set((detail?.mines || []).map((item) => String(item.mine_fid)));
}

export function groupPlotsByMineFid(plotRows = []) {
  const groups = new Map();
  for (const row of plotRows) {
    const key = Number(row.mine_fid);
    if (!groups.has(key)) {
      groups.set(key, []);
    }
    groups.get(key).push(row);
  }
  return groups;
}
```

`miner/src/components/ProjectWorkspace.vue`

```vue
<script setup>
import { buildMineSelectionSet, filterProjects, groupPlotsByMineFid } from '../projectWorkspace/projectWorkspaceHelpers.js';

const selectedMineDetailFid = ref(null);

const plotGroups = computed(() => groupPlotsByMineFid(currentProjectDetail.value?.plots || []));
const selectedMinePlots = computed(() => {
  if (!selectedMineDetailFid.value) return [];
  return plotGroups.value.get(Number(selectedMineDetailFid.value)) || [];
});

watch(
  () => currentProjectDetail.value?.mines,
  (items) => {
    selectedMineDetailFid.value = items?.length ? String(items[0].mine_fid) : null;
  },
  { immediate: true },
);
</script>
```

```vue
<section class="panel">
  <div class="panel-title-row">
    <h2>江西主体矿山</h2>
    <span>{{ currentProjectDetail.mines?.length || 0 }} 个主体</span>
  </div>
  <div class="mine-list">
    <label
      v-for="item in currentProjectDetail.mines || []"
      :key="item.id"
      class="mine-item"
      :class="{ active: String(item.mine_fid) === String(selectedMineDetailFid) }"
    >
      <input v-model="selectedMineDetailFid" type="radio" :value="String(item.mine_fid)" />
      <span>{{ item.mine_name_snapshot }}</span>
      <small>{{ item.city_snapshot || '未标注区域' }} · {{ item.status_snapshot || '状态待补充' }}</small>
    </label>
  </div>
</section>

<section class="panel">
  <div class="panel-title-row">
    <h2>图斑明细</h2>
    <span>{{ selectedMinePlots.length }} 条</span>
  </div>
  <div class="table-list">
    <div v-for="item in selectedMinePlots" :key="item.plot_code" class="table-row table-row-multi">
      <strong>{{ item.plot_code }}</strong>
      <span>{{ item.plot_category || '--' }}</span>
      <span>{{ item.repair_status || '--' }}</span>
      <span>{{ item.repair_mode || '--' }}</span>
      <span>{{ item.area || 0 }}</span>
      <span>{{ item.untreated_area || 0 }}</span>
    </div>
  </div>
</section>
```

- [ ] **Step 4: 运行前后端测试和前端构建**

Run:

```bash
cd backend
python -m unittest test_project_api.py test_jiangxi_seed_service.py -v
cd ..\miner
node --test test/projectWorkspaceHelpers.test.js
npm run build
```

Expected:

```text
OK
pass
built in
```

- [ ] **Step 5: Commit**

```bash
git add backend/test_project_api.py miner/src/components/ProjectWorkspace.vue miner/src/projectWorkspace/projectWorkspaceHelpers.js miner/test/projectWorkspaceHelpers.test.js
git commit -m "feat: show jiangxi aggregated mines and plot details"
```

---

### Task 4: 执行清库导入、更新验证报告并完成验收

**Files:**
- Modify: `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`
- Create or Modify: `backend/seed_jiangxi_from_csv.py`

- [ ] **Step 1: 先写最终回归清单，固定验收命令和预期**

在 `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md` 追加以下验收块：

```md
## 江西空库重建补充验证

- 执行 `python seed_jiangxi_from_csv.py`
- 执行 `python -m unittest test_jiangxi_seed_service.py test_project_api.py -v`
- 执行 `node --test test/projectWorkspaceHelpers.test.js`
- 执行 `npm run build`
- 浏览器登录 `http://127.0.0.1:4000/#/projects`
- 验证工作台不再出现 `云南 / 大理 / 曲靖 / 昆明`
- 验证只出现 `江西矿山生态修复监测项目`
- 验证主体矿山列表和图斑明细可见
```

- [ ] **Step 2: 执行清库与江西导入**

Run:

```bash
cd backend
python seed_jiangxi_from_csv.py
```

Expected:

```text
{'project_name': '江西矿山生态修复监测项目', 'project_count': 1, 'subject_count': 284, 'plot_count': 383}
```

- [ ] **Step 3: 运行回归测试和浏览器验收**

Run:

```bash
cd backend
python -m unittest test_jiangxi_seed_service.py test_project_api.py -v
cd ..\miner
node --test test/projectWorkspaceHelpers.test.js
npm run build
```

Browser checklist:

```text
1. 打开 http://127.0.0.1:4000/#/projects
2. 用 admin + ADMIN_PASSWORD 登录
3. 确认项目列表只有“江西矿山生态修复监测项目”
4. 确认页面中不再出现“云南 / 大理 / 曲靖 / 昆明”
5. 确认主体矿山列表来自江西数据
6. 点击主体后可看到图斑明细
```

- [ ] **Step 4: 更新验证报告为最终结论**

把以下结论写入 `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`：

```md
- 已清空 `analysis` 与 `project*` 旧云南历史数据
- 已从 `D:\项目\江西数据\Mine.csv` 重建江西默认项目
- `/api/projects` 仅返回江西默认项目
- 工作台主体列表和图斑明细均来自江西数据
- 浏览器主流程不再出现 `云南 / 大理 / 曲靖 / 昆明`
```

- [ ] **Step 5: Commit**

```bash
git add backend/seed_jiangxi_from_csv.py docs/superpowers/reports/2026-07-05-formal-delivery-validation.md
git commit -m "feat: rebuild runtime data from jiangxi mine csv"
```

---

## 自检结果

- Spec coverage: 已覆盖清库、江西默认项目、主体聚合、图斑明细、接口复用、前端展示、测试与验收
- Placeholder scan: 未保留 `TBD`、`TODO`、`待定`
- Type consistency: 计划中统一使用 `JiangxiMinePlot`、`aggregate_subject_rows()`、`seed_jiangxi_project_from_csv()`、`groupPlotsByMineFid()`
