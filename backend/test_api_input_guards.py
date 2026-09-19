"""S6/S8 回归（2026-09-19）：interface 层直通分支删除 + show_result limit 钳制。"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from applications import create_app
from applications.common.utils import type_utils
from applications.extensions import db
from applications.interface import analysis as interface_analysis
from applications.models import Analysis


class SpectralInputResolverTests(unittest.TestCase):
    def test_no_exists_passthrough_branch_in_source(self):
        source = (
            Path(__file__).parent / "applications" / "interface" / "analysis.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "os.path.exists(text)", source, "S6：不得保留存在性直通分支"
        )

    def test_bare_existing_filename_is_converged_into_data_path(self):
        # 直通分支残留时可复现的形态：无分隔符但 CWD 下真实存在的文件名
        # 曾被原样作为读取路径返回（逃逸受控 data_path）
        with tempfile.TemporaryDirectory(prefix="s6-cwd-") as cwd, tempfile.TemporaryDirectory(
            prefix="s6-data-"
        ) as data_path:
            stray = Path(cwd) / "plain.tif"
            stray.write_bytes(b"tif")
            previous_cwd = os.getcwd()
            os.chdir(cwd)
            try:
                resolved, name, _ = interface_analysis._resolve_spectral_input(
                    "plain.tif", data_path
                )
            finally:
                os.chdir(previous_cwd)
            self.assertTrue(str(resolved).startswith(str(data_path)))
            self.assertEqual(name, "plain.tif")


class ShowResultLimitClampTests(unittest.TestCase):
    def setUp(self):
        self._device_env_patcher = patch.dict(
            "os.environ", {"JIANGXI_INFERENCE_DEVICE": "cpu"}
        )
        self._device_env_patcher.start()
        self.app = create_app("testing")
        self.app.config["PROPAGATE_EXCEPTIONS"] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.app.config["ADMIN_USERNAME"] = "admin"
        self.app.config["ADMIN_PASSWORD"] = "Secret123!"
        os.environ["ADMIN_USERNAME"] = "admin"
        os.environ["ADMIN_PASSWORD"] = "Secret123!"
        from applications.auth.service import sync_admin_from_env

        sync_admin_from_env()
        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "Secret123!"},
        )
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        self._device_env_patcher.stop()

    def test_limit_is_clamped_to_100(self):
        # Analysis.type 为 Integer：注入的属性值用「光谱指数计算」的索引 8
        with patch.object(type_utils, "s6_probe_type", 8, create=True):
            for i in range(105):
                db.session.add(Analysis(type=8, data=None, checked="1"))
            db.session.commit()

            response = self.client.get("/api/analysis/show/s6_probe_type?limit=5000")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertLessEqual(len(payload.get("data") or []), 100)

    def test_zero_limit_falls_back_to_floor(self):
        with patch.object(type_utils, "s6_probe_type", 8, create=True):
            db.session.add(Analysis(type=8, data=None, checked="1"))
            db.session.commit()

            response = self.client.get("/api/analysis/show/s6_probe_type?limit=0")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(len(payload.get("data") or []), 1)


if __name__ == "__main__":
    unittest.main()
