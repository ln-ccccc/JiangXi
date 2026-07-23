"""Source-level isolation contracts outside Docker Compose."""

import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


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

    def test_backend_runtime_explicitly_disables_debug_reloader_in_production(self):
        source = (ROOT / "backend" / "app.py").read_text(encoding="utf-8")

        self.assertIn("debug=debug_mode", source)
        self.assertIn("use_reloader=debug_mode", source)

    def test_runtime_scripts_do_not_bootstrap_legacy_model_source(self):
        scripts = [
            ROOT / "docker" / "start-backend.sh",
            ROOT / "docker" / "start-miner-api.sh",
            ROOT / "docker" / "entrypoint.sh",
        ]
        source = "\n".join(path.read_text(encoding="utf-8") for path in scripts)

        self.assertNotIn("dinov3_swinV1", source)
        self.assertNotIn("model/mmseg_config", source)
        self.assertIn("JIANGXI_MMSEG_SOURCE_ROOT", source)

    def test_default_jiangxi_kmz_contains_all_polygon_boundaries(self):
        kmz_path = (
            ROOT
            / "docker"
            / "standalone"
            / "runtime_data"
            / "Jiangxi_NaturalMine.kmz"
        )
        with ZipFile(kmz_path) as archive:
            root = ET.fromstring(archive.read("doc.kml"))

        namespace = {"kml": "http://www.opengis.net/kml/2.2"}
        polygon_placemarks = [
            placemark
            for placemark in root.findall(".//kml:Placemark", namespace)
            if placemark.find(".//kml:Polygon", namespace) is not None
        ]
        fids = [
            (placemark.findtext("kml:name", default="", namespaces=namespace)).strip()
            for placemark in polygon_placemarks
        ]

        self.assertEqual(len(polygon_placemarks), 348)
        self.assertEqual(fids[0], "23")
        self.assertEqual(
            sorted(int(fid) for fid in fids),
            list(range(1, 349)),
        )


if __name__ == "__main__":
    unittest.main()
