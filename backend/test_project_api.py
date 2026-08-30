import csv
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from applications import create_app
from applications.extensions import db


class TestProjectAPI(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app.config["PROPAGATE_EXCEPTIONS"] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.temp_dir = tempfile.mkdtemp(prefix="project-api-")
        self.output_root = Path(self.temp_dir) / "managed-output"
        self.app.config["PROJECT_OUTPUT_ROOT"] = str(self.output_root)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _json(self, response):
        return json.loads(response.data.decode("utf-8"))

    def _build_minimal_jiangxi_csv(self):
        csv_path = Path(self.temp_dir) / "Mine.csv"
        header = [
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
                "2024-12",
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
            ]
        ]
        with csv_path.open("w", encoding="gbk", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(header)
            writer.writerows(rows)
        return csv_path

    def _build_minimal_jiangxi_workbook(self):
        workbook_path = Path(self.temp_dir) / "jiangxi.xlsx"
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["FID", "TBBH", "SHI", "XIAN", "面积", "矿山位置_"])
        worksheet.append([0, "SUBJECT-1", "宜春市", "高安市", 10000, "江西省宜春市高安市村A"])
        workbook.save(workbook_path)
        return workbook_path

    def _build_minimal_jiangxi_manifest(self):
        manifest_path = Path(self.temp_dir) / "Jiangxi_asset_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "status": "ok",
                    "mapping": {"tbbh_to_map_fid": {"SUBJECT-1": 1}},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return manifest_path

    def sync_admin(self, password="Secret123!"):
        os.environ["ADMIN_USERNAME"] = "admin"
        os.environ["ADMIN_PASSWORD"] = password
        self.app.config["ADMIN_USERNAME"] = "admin"
        self.app.config["ADMIN_PASSWORD"] = password
        from applications.auth.service import sync_admin_from_env

        return sync_admin_from_env()

    def login_as_admin(self, password="Secret123!"):
        self.sync_admin(password)
        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": password},
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_project_workflow_crud_binding_dataset_timeline_and_status(self):
        self.login_as_admin()
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
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        project_id = body["data"]["id"]

        response = self.client.get("/api/projects")
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        self.assertEqual(len(body["data"]["items"]), 1)
        self.assertEqual(body["data"]["items"][0]["mine_count"], 0)
        self.assertEqual(body["data"]["items"][0]["dataset_count"], 0)

        response = self.client.put(
            f"/api/projects/{project_id}/mines",
            json={
                "mines": [
                    {
                        "tbbh": "TBBH-101",
                        "mine_name_snapshot": "赣州矿山A",
                        "city_snapshot": "赣州市",
                        "area_snapshot": 12.5,
                        "status_snapshot": "待治理",
                        "sort_order": 1,
                    },
                    {
                        "tbbh": "TBBH-102",
                        "mine_name_snapshot": "宜春矿山B",
                        "city_snapshot": "宜春市",
                        "area_snapshot": 9.8,
                        "status_snapshot": "已治理",
                        "sort_order": 2,
                    },
                ]
            },
        )
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["mine_count"], 2)

        response = self.client.post(
            f"/api/projects/{project_id}/datasets",
            json={
                "dataset_kind": "imagery",
                "display_name": "2024年春季影像",
                "file_path": os.path.join(self.temp_dir, "imagery_2024.tif"),
                "source_format": "tif",
                "tbbh": "TBBH-101",
                "year_start": 2024,
                "year_end": 2024,
                "slice_config_json": {"slice_size": 1024, "padding": 64},
            },
        )
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        dataset_id = body["data"]["id"]

        response = self.client.get(f"/api/projects/{project_id}")
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        detail = body["data"]
        self.assertEqual(detail["summary"]["id"], project_id)
        self.assertEqual(detail["summary"]["mine_count"], 2)
        self.assertEqual(detail["summary"]["dataset_count"], 1)
        self.assertEqual(len(detail["mines"]), 2)
        self.assertEqual(len(detail["datasets"]), 1)
        self.assertEqual(detail["datasets"][0]["id"], dataset_id)
        self.assertIn("recent_activity", detail)
        self.assertGreaterEqual(len(detail["recent_activity"]), 3)

        response = self.client.get(f"/api/projects/{project_id}/timeline")
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        timeline = body["data"]["items"]
        self.assertGreaterEqual(len(timeline), 3)
        self.assertIn("dataset_created", {item["event_type"] for item in timeline})

        response = self.client.post(f"/api/projects/{project_id}/archive", json={})
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["status"], "archived")

        response = self.client.post(f"/api/projects/{project_id}/restore", json={})
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["status"], "active")

    def test_project_export_and_backup_restore(self):
        self.login_as_admin()
        response = self.client.post(
            "/api/projects",
            json={
                "name": "江西治理项目",
                "region": "江西省",
                "manager": "李四",
                "monitor_start_year": 2023,
                "monitor_end_year": 2025,
            },
        )
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        project_id = body["data"]["id"]

        self.client.put(
            f"/api/projects/{project_id}/mines",
            json={
                "mines": [
                    {
                        "tbbh": "TBBH-201",
                        "mine_name_snapshot": "上饶矿山A",
                        "city_snapshot": "上饶市",
                        "area_snapshot": 4.2,
                        "status_snapshot": "待治理",
                        "sort_order": 1,
                    }
                ]
            },
        )

        response = self.client.post(
            f"/api/projects/{project_id}/datasets",
            json={
                "dataset_kind": "report",
                "display_name": "2025趋势报告",
                "file_path": os.path.join(self.temp_dir, "trend_report.csv"),
                "source_format": "csv",
                "tbbh": "TBBH-201",
                "year_start": 2024,
                "year_end": 2025,
                "slice_config_json": {},
            },
        )
        body = self._json(response)
        dataset_id = body["data"]["id"]

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[100.0, 25.0], [100.1, 25.0], [100.1, 25.1], [100.0, 25.1], [100.0, 25.0]]],
            },
            "properties": {
                "tbbh": "TBBH-201",
                "dataset_id": dataset_id,
                "result_type": "report",
                "year_start": 2024,
                "year_end": 2025,
            },
        }

        response = self.client.post(
            f"/api/projects/{project_id}/exports",
            json={
                "format": "geojson",
                "features": [feature],
            },
        )
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        geojson_path = body["data"]["file_path"]
        self.assertTrue(os.path.exists(geojson_path))
        self.assertTrue(Path(geojson_path).is_relative_to(self.output_root / "exports" / str(project_id)))

        response = self.client.post(
            f"/api/projects/{project_id}/exports",
            json={
                "format": "csv",
            },
        )
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        csv_path = body["data"]["file_path"]
        self.assertTrue(os.path.exists(csv_path))

        response = self.client.get(f"/api/projects/{project_id}/exports")
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        self.assertEqual(len(body["data"]["items"]), 2)

        response = self.client.post(
            f"/api/projects/{project_id}/backups",
            json={"scope": "metadata_index"},
        )
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        backup_id = body["data"]["id"]
        manifest_path = body["data"]["manifest_path"]
        self.assertTrue(os.path.exists(manifest_path))
        self.assertTrue(Path(manifest_path).is_relative_to(self.output_root / "backups" / str(project_id)))

        response = self.client.patch(
            f"/api/projects/{project_id}",
            json={"name": "江西治理项目-已改名", "remark": "restore-target"},
        )
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["name"], "江西治理项目-已改名")

        response = self.client.post(f"/api/projects/{project_id}/archive", json={})
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["status"], "archived")

        response = self.client.post(f"/api/projects/{project_id}/backups/{backup_id}/restore", json={})
        body = self._json(response)
        self.assertEqual(body["code"], 0)
        restored = body["data"]
        self.assertEqual(restored["summary"]["name"], "江西治理项目")
        self.assertEqual(restored["summary"]["status"], "active")
        self.assertEqual(len(restored["datasets"]), 1)
        self.assertEqual(len(restored["exports"]), 2)

    def test_project_export_rejects_client_output_directory(self):
        self.login_as_admin()
        response = self.client.post(
            "/api/projects",
            json={"name": "测试项目", "region": "江西省"},
        )
        project_id = self._json(response)["data"]["id"]

        response = self.client.post(
            f"/api/projects/{project_id}/exports",
            json={"format": "csv", "output_dir": self.temp_dir},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._json(response)["success"], False)

    def test_backup_restore_rejects_manifest_outside_managed_root(self):
        from applications.models.project import ProjectBackupRecord

        self.login_as_admin()
        project_id = self._json(
            self.client.post("/api/projects", json={"name": "测试项目", "region": "江西省"})
        )["data"]["id"]
        backup_id = self._json(
            self.client.post(f"/api/projects/{project_id}/backups", json={"scope": "metadata_index"})
        )["data"]["id"]
        outside_manifest = Path(self.temp_dir) / "outside.json"
        outside_manifest.write_text("{}", encoding="utf-8")
        backup = ProjectBackupRecord.query.get(backup_id)
        backup.manifest_path = str(outside_manifest)
        db.session.commit()

        response = self.client.post(f"/api/projects/{project_id}/backups/{backup_id}/restore", json={})

        self.assertEqual(response.status_code, 400)

    def test_project_backup_rejects_client_output_directory(self):
        self.login_as_admin()
        project_id = self._json(
            self.client.post("/api/projects", json={"name": "测试项目", "region": "江西省"})
        )["data"]["id"]

        response = self.client.post(
            f"/api/projects/{project_id}/backups",
            json={"scope": "metadata_index", "output_dir": self.temp_dir},
        )

        self.assertEqual(response.status_code, 400)

    def test_project_detail_contains_jiangxi_plot_rows(self):
        from applications.project_hub.jiangxi_seed_service import seed_jiangxi_project_from_csv

        self.login_as_admin()
        csv_path = self._build_minimal_jiangxi_csv()
        seed_jiangxi_project_from_csv(
            csv_path,
            actor="test",
            workbook_path=self._build_minimal_jiangxi_workbook(),
            manifest_path=self._build_minimal_jiangxi_manifest(),
        )

        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 200)
        project_id = self._json(response)["data"]["items"][0]["id"]

        detail_response = self.client.get(f"/api/projects/{project_id}")
        self.assertEqual(detail_response.status_code, 200)
        detail = self._json(detail_response)["data"]

        self.assertEqual(detail["summary"]["region"], "江西省")
        self.assertGreaterEqual(len(detail["mines"]), 1)
        self.assertGreaterEqual(len(detail["plots"]), 1)
        self.assertEqual(detail["plots"][0]["tbbh"], "SUBJECT-1")


if __name__ == "__main__":
    unittest.main()
