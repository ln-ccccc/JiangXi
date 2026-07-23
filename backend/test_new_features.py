import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from applications import create_app
from applications.extensions import db
from applications.region_source import load_kml_root


class TestNewFeatures(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app.config["PROPAGATE_EXCEPTIONS"] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _json(self, response):
        return json.loads(response.data.decode("utf-8"))

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

    def test_model_list_requires_login(self):
        response = self.client.get("/api/model/list/registration")
        self.assertEqual(response.status_code, 401)
        body = self._json(response)
        self.assertEqual(body["code"], 401)

    def test_supported_model_lists(self):
        self.login_as_admin()
        cases = {
            "registration": "register",
            "tracking": "tracker",
            "object_detection": "detector",
        }

        for model_type, expected_model_type in cases.items():
            response = self.client.get(f"/api/model/list/{model_type}")
            self.assertEqual(response.status_code, 200)
            body = self._json(response)
            self.assertEqual(body["code"], 0)
            items = body["data"]
            self.assertTrue(items)
            self.assertTrue(all(item["model_type"] == expected_model_type for item in items))

        object_detection = self._json(self.client.get("/api/model/list/object_detection"))["data"]
        self.assertTrue(
            any(str(item.get("model_path", "")).startswith("mmrotate:") for item in object_detection)
        )

    def test_invalid_model_type(self):
        self.login_as_admin()
        response = self.client.get("/api/model/list/not_real")
        self.assertEqual(response.status_code, 200)
        body = self._json(response)
        self.assertEqual(body["code"], 1)

    def test_kml_roi_history_rejects_traversal_record_id(self):
        from applications.api import analysis as analysis_module

        self.login_as_admin()
        temp_dir = Path(tempfile.mkdtemp(prefix="analysis-output-"))
        outside_file = temp_dir.parent / "outside.png"
        outside_file.write_bytes(b"protected")
        previous_root = analysis_module.miner_change_output_root
        analysis_module.miner_change_output_root = temp_dir
        try:
            response = self.client.delete(
                "/api/analysis/kml_roi_history/item",
                json={"record_id": "..|outside.png"},
            )
        finally:
            analysis_module.miner_change_output_root = previous_root

        self.assertEqual(response.status_code, 400)
        self.assertTrue(outside_file.exists())
        outside_file.unlink()
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_kml_roi_inference_rejects_client_paths_and_uses_managed_inputs(self):
        input_root = Path(tempfile.mkdtemp(prefix="roi-input-"))
        kml_root = Path(tempfile.mkdtemp(prefix="roi-kml-"))
        (input_root / "old.tif").write_bytes(b"tif")
        (kml_root / "roi.kml").write_text("<kml></kml>", encoding="utf-8")
        self.app.config["KML_ROI_INPUT_ROOT"] = str(input_root)
        self.app.config["KML_ROI_KML_ROOT"] = str(kml_root)
        self.login_as_admin()
        try:
            with patch("applications.api.analysis.run_kml_roi_inference") as run_inference:
                rejected = self.client.post(
                    "/api/analysis/kml_roi_inference",
                    json={
                        "old_tif_path": str(input_root / "old.tif"),
                        "output_root": str(input_root),
                    },
                )
                self.assertEqual(rejected.status_code, 400)
                run_inference.assert_not_called()

                run_inference.return_value = {"ok": True}
                accepted = self.client.post(
                    "/api/analysis/kml_roi_inference",
                    json={"old_tif_path": "old.tif", "kml_path": "roi.kml"},
                )
                self.assertEqual(accepted.status_code, 200)
                self.assertEqual(run_inference.call_args.kwargs["old_tif_path"], str(input_root / "old.tif"))
                self.assertEqual(run_inference.call_args.kwargs["kml_path"], str(kml_root / "roi.kml"))

                accepted_upload_path = self.client.post(
                    "/api/analysis/kml_roi_inference",
                    json={
                        "old_tif_path": "static/upload/old.tif",
                        "kml_path": "roi.kml",
                    },
                )
                self.assertEqual(accepted_upload_path.status_code, 200)
                self.assertEqual(
                    run_inference.call_args.kwargs["old_tif_path"],
                    str(input_root / "old.tif"),
                )

                rejected_other_prefix = self.client.post(
                    "/api/analysis/kml_roi_inference",
                    json={
                        "old_tif_path": "other/old.tif",
                        "kml_path": "roi.kml",
                    },
                )
                self.assertEqual(rejected_other_prefix.status_code, 400)
        finally:
            shutil.rmtree(input_root, ignore_errors=True)
            shutil.rmtree(kml_root, ignore_errors=True)

    def test_kml_roi_inference_uses_configured_default_kmz_filename(self):
        input_root = Path(tempfile.mkdtemp(prefix="roi-config-input-"))
        (input_root / "old.tif").write_bytes(b"tif")
        configured_kmz = (
            Path(__file__).resolve().parents[1]
            / "docker"
            / "standalone"
            / "runtime_data"
            / "Jiangxi_NaturalMine.kmz"
        )
        parsed_root = load_kml_root(configured_kmz)
        self.assertEqual(parsed_root.tag, "{http://www.opengis.net/kml/2.2}kml")
        self.assertTrue(
            parsed_root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
        )
        self.app.config["KML_ROI_INPUT_ROOT"] = str(input_root)
        self.app.config["KML_ROI_KML_ROOT"] = str(configured_kmz.parent)
        self.app.config["MINER_DEFAULT_KMZ_PATH"] = "/app/runtime_data/Jiangxi_NaturalMine.kmz"
        self.login_as_admin()
        try:
            with patch("applications.api.analysis.run_kml_roi_inference") as run_inference:
                run_inference.return_value = {"ok": True}
                response = self.client.post(
                    "/api/analysis/kml_roi_inference",
                    json={"old_tif_path": "old.tif"},
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(run_inference.call_args.kwargs["kml_path"], str(configured_kmz))
        finally:
            shutil.rmtree(input_root, ignore_errors=True)

    def test_kml_roi_inference_returns_failure_when_all_tiles_fail(self):
        input_root = Path(tempfile.mkdtemp(prefix="roi-failed-input-"))
        kml_root = Path(tempfile.mkdtemp(prefix="roi-failed-kml-"))
        (input_root / "old.tif").write_bytes(b"tif")
        (kml_root / "roi.kml").write_text("<kml></kml>", encoding="utf-8")
        self.app.config["KML_ROI_INPUT_ROOT"] = str(input_root)
        self.app.config["KML_ROI_KML_ROOT"] = str(kml_root)
        self.login_as_admin()
        try:
            with patch("applications.api.analysis.run_kml_roi_inference") as run_inference:
                run_inference.return_value = {
                    "status": "failed",
                    "matched_fids": 1,
                    "written_fids": 0,
                    "failed_tiles": ["23+2026_tile.png"],
                    "tile_errors": {
                        "23+2026_tile.png": "江西地物分类模型文件不存在"
                    },
                }
                response = self.client.post(
                    "/api/analysis/kml_roi_inference",
                    json={"old_tif_path": "old.tif", "kml_path": "roi.kml"},
                )

            body = self._json(response)
            self.assertEqual(response.status_code, 500)
            self.assertFalse(body["success"])
            self.assertEqual(body["data"]["status"], "failed")
            self.assertIn("江西地物分类模型文件不存在", body["msg"])
        finally:
            shutil.rmtree(input_root, ignore_errors=True)
            shutil.rmtree(kml_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
