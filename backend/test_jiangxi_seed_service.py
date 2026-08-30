import csv
import json
import os
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from applications import create_app
from applications.extensions import db
from applications.models.analysis import Analysis
from applications.models.jiangxi_seed import JiangxiMinePlot
from applications.models.project import Project
from applications.models.project import ProjectActivityLog, ProjectMineBinding
from applications.project_hub.jiangxi_seed_service import (
    aggregate_subject_rows,
    build_map_aligned_records,
    get_jiangxi_seed_database_state,
    reset_project_domain_tables,
    seed_jiangxi_project_from_csv,
    sync_jiangxi_project_from_workbook,
)


CSV_HEADER = [
    "Lon",
    "Lat",
    "No",
    "省市",
    "地市",
    "区县",
    "矿山位置",
    "主体编号",
    "图斑编号",
    "修复图斑编号",
    "中心经度",
    "中心纬度",
    "Area",
    "图斑小类",
    "修复状态",
    "修复模式",
    "完成时间",
    "Area2",
    "未治理面积",
    "填报单位",
    "填报人",
    "填报日期",
    "备注",
    "矿种",
    "开采方式",
    "关闭年度",
    "图斑属性",
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
            [
                "115.1",
                "28.1",
                "1",
                "江西省",
                "宜春市",
                "高安市",
                "江西省宜春市高安市村A",
                "SUBJECT-1",
                "PLOT-1",
                "PLOT-1",
                "115.1",
                "28.1",
                "100",
                "政策性关闭矿山",
                "完全修复",
                "自然恢复",
                "Dec-24",
                "100",
                "0",
                "高安市自然资源局",
                "甲",
                "2024-12-31",
                "",
                "84412",
                "A",
                "2017",
                "1",
            ],
            [
                "115.2",
                "28.2",
                "2",
                "江西省",
                "宜春市",
                "高安市",
                "江西省宜春市高安市村A",
                "SUBJECT-1",
                "PLOT-2",
                "PLOT-2",
                "115.2",
                "28.2",
                "50",
                "政策性关闭矿山",
                "部分修复",
                "自然恢复",
                "Dec-24",
                "45",
                "5",
                "高安市自然资源局",
                "甲",
                "2025-01-01",
                "",
                "84412",
                "A",
                "2017",
                "4",
            ],
            [
                "116.3",
                "28.3",
                "3",
                "江西省",
                "南昌市",
                "进贤县",
                "江西省南昌市进贤县村B",
                "SUBJECT-2",
                "PLOT-3",
                "PLOT-3",
                "116.3",
                "28.3",
                "80",
                "无主废弃矿山",
                "完全修复",
                "自然恢复",
                "Dec-23",
                "80",
                "0",
                "进贤县自然资源局",
                "乙",
                "2024-01-06",
                "",
                "84412",
                "A",
                "2018",
                "1",
            ],
        ]
        with csv_path.open("w", encoding="gbk", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(CSV_HEADER)
            writer.writerows(rows)
        return csv_path

    def _write_workbook(self):
        temp_dir = Path(tempfile.mkdtemp(prefix="jiangxi_workbook_"))
        workbook_path = temp_dir / "348图斑_TableMERNet无图像预测结果.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(
            [
                "FID",
                "TBBH",
                "SHI",
                "XIAN",
                "面积",
                "矿山位置_",
                "修复状态",
                "修复模式",
                "完成时间",
                "图斑小类",
                "未治理面积",
                "中心经度_",
                "中心纬度_",
            ]
        )
        sheet.append(
            [
                0,
                "TBBH-000",
                "南昌市",
                "进贤县",
                10000,
                "江西省南昌市进贤县示例图斑 A",
                "完全修复",
                "自然恢复",
                "2024-12",
                "历史遗留废弃矿山",
                0,
                116.2,
                28.3,
            ]
        )
        sheet.append(
            [
                1,
                "TBBH-001",
                "宜春市",
                "高安市",
                25000,
                "江西省宜春市高安市示例图斑 B",
                "完全修复",
                "工程修复",
                "2025-01",
                "历史遗留废弃矿山",
                0,
                115.4,
                28.4,
            ]
        )
        workbook.save(workbook_path)
        return workbook_path

    def _write_manifest(self):
        temp_dir = Path(tempfile.mkdtemp(prefix="jiangxi_manifest_"))
        manifest_path = temp_dir / "Jiangxi_asset_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "status": "ok",
                    "mapping": {"tbbh_to_map_fid": {"TBBH-000": 1, "TBBH-001": 2}},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return manifest_path

    def test_aggregate_subject_rows_groups_by_subject_code(self):
        csv_path = self._write_csv()
        subjects, skipped, warnings, total_rows = aggregate_subject_rows(csv_path)

        self.assertEqual(skipped, 0)
        self.assertEqual(total_rows, 3)
        self.assertEqual(warnings, [])
        self.assertEqual(len(subjects), 2)
        first = next(item for item in subjects if item["subject_code"] == "SUBJECT-1")
        self.assertEqual(first["plot_count"], 2)
        self.assertEqual(first["area_total"], 150.0)
        self.assertEqual(first["untreated_area_total"], 5.0)
        self.assertEqual(first["city"], "宜春市")
        self.assertEqual(len(first["plots"]), 2)

    def test_reset_project_domain_tables_clears_project_and_analysis_rows(self):
        db.session.add(Project(name="云南项目", region="云南省", status="active"))
        db.session.add(Analysis(type=1, before_img="a.png"))
        db.session.commit()

        reset_project_domain_tables()

        self.assertEqual(Project.query.count(), 0)
        self.assertEqual(Analysis.query.count(), 0)

    def test_jiangxi_seed_database_state_distinguishes_empty_ready_and_invalid(self):
        self.assertEqual(get_jiangxi_seed_database_state(), "empty")

        db.session.add(
            Project(
                name="江西矿山生态修复监测项目",
                region="江西省",
                remark="system_seed:jiangxi_tbbh",
                status="active",
            )
        )
        db.session.commit()
        self.assertEqual(get_jiangxi_seed_database_state(), "ready")

        db.session.query(Project).delete()
        db.session.add(Project(name="其他项目", region="江西省", status="active"))
        db.session.commit()
        self.assertEqual(get_jiangxi_seed_database_state(), "invalid")

    def test_seed_jiangxi_project_from_csv_creates_default_project_bindings_and_plots(self):
        csv_path = self._write_csv()

        with self.assertRaisesRegex(ValueError, "必须提供权威 Excel"):
            seed_jiangxi_project_from_csv(csv_path, actor="system")

        self.assertEqual(Project.query.count(), 0)
        self.assertEqual(ProjectMineBinding.query.count(), 0)
        self.assertEqual(JiangxiMinePlot.query.count(), 0)

    def test_sync_jiangxi_project_from_workbook_replaces_subject_bindings_with_map_plots(self):
        manifest_path = self._write_manifest()
        seed_jiangxi_project_from_csv(
            self._write_csv(),
            actor="system",
            workbook_path=self._write_workbook(),
            manifest_path=manifest_path,
        )

        result = sync_jiangxi_project_from_workbook(
            self._write_workbook(), actor="system", manifest_path=manifest_path
        )

        self.assertEqual(result["mine_count"], 2)
        self.assertEqual(result["plot_count"], 2)
        self.assertEqual(ProjectMineBinding.query.count(), 2)
        self.assertEqual(JiangxiMinePlot.query.count(), 2)

        project = Project.query.first()
        self.assertEqual(project.monitor_start_year, 2013)
        self.assertEqual(project.monitor_end_year, 2025)
        first_binding = ProjectMineBinding.query.order_by(ProjectMineBinding.tbbh.asc()).first()
        self.assertEqual(first_binding.tbbh, "TBBH-000")
        self.assertEqual(first_binding.mine_name_snapshot, "江西省南昌市进贤县示例图斑 A")
        self.assertEqual(round(first_binding.area_snapshot, 2), 1.0)
        first_plot = JiangxiMinePlot.query.order_by(JiangxiMinePlot.tbbh.asc()).first()
        self.assertEqual(first_plot.tbbh, "TBBH-000")
        self.assertEqual(first_plot.plot_code, "TBBH-000")

    def test_build_map_aligned_records_accepts_excel_fid_zero(self):
        records = build_map_aligned_records(
            self._write_workbook(),
            {"TBBH-000": 23, "TBBH-001": 24},
        )

        first = next(record for record in records if record["tbbh"] == "TBBH-000")
        self.assertEqual(first["excel_fid"], 0)
        self.assertEqual(first["map_fid"], 23)


class SQLiteProductionConfigTestCase(unittest.TestCase):
    def test_production_config_uses_sqlite_when_db_backend_is_sqlite(self):
        sqlite_path = Path(tempfile.mkdtemp(prefix="jiangxi_sqlite_")) / "jiangxi.sqlite3"
        old_backend = os.environ.get("DB_BACKEND")
        old_path = os.environ.get("SQLITE_PATH")
        old_secret = os.environ.get("SECRET_KEY")
        old_admin_password = os.environ.get("ADMIN_PASSWORD")
        try:
            os.environ["DB_BACKEND"] = "sqlite"
            os.environ["SQLITE_PATH"] = str(sqlite_path)
            os.environ["SECRET_KEY"] = "sqlite-test-secret"
            os.environ["ADMIN_PASSWORD"] = "sqlite-admin-pass"
            app = create_app("production")
            uri = app.config["SQLALCHEMY_DATABASE_URI"]
            self.assertTrue(uri.startswith("sqlite:///"))
            self.assertIn("jiangxi.sqlite3", uri)
        finally:
            if old_backend is None:
                os.environ.pop("DB_BACKEND", None)
            else:
                os.environ["DB_BACKEND"] = old_backend
            if old_path is None:
                os.environ.pop("SQLITE_PATH", None)
            else:
                os.environ["SQLITE_PATH"] = old_path
            if old_secret is None:
                os.environ.pop("SECRET_KEY", None)
            else:
                os.environ["SECRET_KEY"] = old_secret
            if old_admin_password is None:
                os.environ.pop("ADMIN_PASSWORD", None)
            else:
                os.environ["ADMIN_PASSWORD"] = old_admin_password
