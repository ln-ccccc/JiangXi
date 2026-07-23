"""Source-level isolation contracts outside Docker Compose."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class JiangxiSourceIsolationTests(unittest.TestCase):
    def test_data_preparation_uses_only_project_scoped_jiangxi_sources(self):
        source = (ROOT / "scripts" / "process_mine_data.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("MINER_DEFAULT_GEO_SOURCE_PATH", source)
        self.assertIn("MINER_ECOLOGY_WORKBOOK_PATH", source)
        self.assertIn("348个图斑.shp", source)
        self.assertIn("348图斑_TableMERNet无图像预测结果.xlsx", source)
        self.assertNotIn("YunNan", source)
        self.assertNotIn("Wechat", source)
        self.assertNotIn("prechange", source.lower())

    def test_miner_runtime_source_has_no_yunnan_place_name(self):
        source = (ROOT / "miner" / "src" / "composables" / "useWeather.js").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("Dali", source)
        self.assertNotIn("Yunnan", source)

    def test_jiangxi_interpretation_source_has_no_async_job_api(self):
        frontend_source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "frontend" / "src").rglob("*")
            if path.is_file() and path.suffix in {".js", ".vue"}
        )

        self.assertNotIn("/api/inference/jobs", frontend_source)
        self.assertNotIn("yunnan.kml", frontend_source.lower())


if __name__ == "__main__":
    unittest.main()
