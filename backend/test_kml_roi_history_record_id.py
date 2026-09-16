"""2026-09-16 审查 P2-1 回归：kml_roi 历史删除接口的 record_id 解析加固。

契约（前端冻结为 2 段 `${tbbh}|${name}`）：后端取「首段为 tbbh、末段为
filename」，同时兼容历史 3 段式 `tbbh|map_fid|name`（推理完成 flash 卡片
曾按此生成，split("|", 1) 会把 "map_fid|name" 整段当文件名，删除必然
「记录不存在」）。
"""

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
from applications.api import analysis as analysis_module
from applications.extensions import db

MANIFEST = {"status": "ok", "mapping": {"tbbh_to_map_fid": {"TBBH-1": 11192}}}


class KmlRoiHistoryRecordIdTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app.config["PROPAGATE_EXCEPTIONS"] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        with self.client.session_transaction() as sess:
            sess["admin_user_id"] = 1

        self.output_root = Path(tempfile.mkdtemp(prefix="kml-record-id-"))
        self.manifest_path = self.output_root / "manifest.json"
        self.manifest_path.write_text(json.dumps(MANIFEST), encoding="utf-8")
        fid_dir = self.output_root / "11192"
        fid_dir.mkdir()
        (fid_dir / "result_manifest.json").write_text(
            json.dumps({"map_fid": 11192, "tbbh": "TBBH-1"}), encoding="utf-8"
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        shutil.rmtree(self.output_root, ignore_errors=True)

    def _seed_output(self, filename):
        (self.output_root / "11192" / filename).write_bytes(b"png")
        return self.output_root / "11192" / filename

    def _delete(self, record_id):
        with patch.object(
            analysis_module, "miner_change_output_root", self.output_root
        ), patch.object(
            analysis_module, "_asset_manifest_path", return_value=self.manifest_path
        ):
            return self.client.delete(
                "/api/analysis/kml_roi_history/item", json={"record_id": record_id}
            )

    def test_delete_accepts_legacy_three_part_record_id(self):
        # P2-1 主回归：历史 flash 卡片 3 段式 tbbh|map_fid|name 可正确删除
        target = self._seed_output("11192+2024.png")
        self._seed_output("11192+2024_src.png")

        response = self._delete("TBBH-1|11192|11192+2024.png")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["msg"], "删除成功")
        self.assertFalse(target.exists())
        self.assertFalse((self.output_root / "11192" / "11192+2024_src.png").exists())

    def test_delete_accepts_two_part_record_id_from_history_list(self):
        # 现行历史列表产出的 2 段式 tbbh|name 行为不变
        target = self._seed_output("11192+2024.png")

        response = self._delete("TBBH-1|11192+2024.png")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["msg"], "删除成功")
        self.assertFalse(target.exists())

    def test_delete_rejects_record_id_without_separator(self):
        response = self._delete("TBBH-1-11192+2024.png")
        body = response.get_json()
        self.assertEqual(body["msg"], "参数异常")

    def test_delete_rejects_empty_segments(self):
        response = self._delete("|11192+2024.png")
        self.assertEqual(response.get_json()["msg"], "参数异常")
        response = self._delete("TBBH-1|11192|")
        self.assertEqual(response.get_json()["msg"], "参数异常")

    def test_delete_rejects_path_like_tbbh(self):
        response = self._delete("../etc|11192+2024.png")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["msg"], "TBBH 参数不合法")

    def test_delete_unknown_tbbh_returns_404(self):
        self._seed_output("11192+2024.png")
        response = self._delete("TBBH-404|11192+2024.png")
        self.assertEqual(response.status_code, 404)
        self.assertIn("TBBH 不存在", response.get_json()["msg"])

    def test_delete_missing_file_reports_record_missing(self):
        # 未匹配的中间段不得被当作文件名（3 段式中段只是 map_fid）
        self._seed_output("11192+2024.png")
        response = self._delete("TBBH-1|99999|11192+2024.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["msg"], "删除成功")
        self.assertFalse((self.output_root / "11192" / "11192+2024.png").exists())


if __name__ == "__main__":
    unittest.main()
