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

    def test_seed_runtime_recovers_only_an_empty_database_when_marker_remains(self):
        source = (
            ROOT / "docker" / "standalone" / "seed-jiangxi-runtime.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("get_jiangxi_seed_database_state", source)
        self.assertIn("contextlib.redirect_stdout", source)
        self.assertIn("empty)", source)
        self.assertIn("residual domain data; manual recovery required", source)
        self.assertIn("--sync-existing", source)

    def test_standalone_image_uses_controlled_upload_root(self):
        source = (
            ROOT / "docker" / "standalone" / "Dockerfile.jiangxi"
        ).read_text(encoding="utf-8")

        self.assertIn("KML_ROI_INPUT_ROOT=/app/backend/static/upload", source)

    def test_standalone_image_has_offline_selectable_base_and_vendored_mmseg_check(self):
        source = (
            ROOT / "docker" / "standalone" / "Dockerfile.jiangxi"
        ).read_text(encoding="utf-8")

        self.assertIn("ARG JIANGXI_BASE_IMAGE=jiangxi-runtime:current", source)
        self.assertIn("FROM ${JIANGXI_BASE_IMAGE}", source)
        self.assertIn(
            'PYTHONPATH="/app/backend/model/jiangxi/dinov3_swinV1:${PYTHONPATH:-}"',
            source,
        )
        self.assertIn("mmdet_init", source)
        self.assertIn("mmcv_maximum_version", source)
        self.assertIn("2.3.0", source)
        self.assertIn("rollup-linux-x64-gnu", source)
        self.assertIn("@esbuild/linux-x64", source)
        self.assertIn("npm ci --offline", source)

    def test_online_satellite_is_the_default_map_provider(self):
        dockerfile = (ROOT / "docker" / "standalone" / "Dockerfile.jiangxi").read_text(
            encoding="utf-8"
        )
        entrypoint = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")
        standalone = (
            ROOT / "docker" / "standalone" / "start-jiangxi-standalone.sh"
        ).read_text(encoding="utf-8")
        compose = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

        self.assertIn("MINER_MAP_PROVIDER=gaode", dockerfile)
        self.assertIn("${MINER_MAP_PROVIDER:-gaode}", entrypoint)
        self.assertIn("${MINER_MAP_PROVIDER:-gaode}", standalone)
        self.assertIn("${MINER_MAP_PROVIDER:-gaode}", compose)

    def test_standalone_entrypoint_forces_sqlite_over_external_database_env(self):
        standalone = (
            ROOT / "docker" / "standalone" / "start-jiangxi-standalone.sh"
        ).read_text(encoding="utf-8")
        entrypoint = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")

        self.assertIn('export DB_BACKEND="sqlite"', standalone)
        self.assertIn('export DB_BACKEND="sqlite"', entrypoint)
        self.assertIn('VUE_APP_MINER_URL="${VUE_APP_MINER_URL:-http://127.0.0.1:4173/}"', entrypoint)
        self.assertIn('VUE_APP_BACKEND_URL="${VUE_APP_BACKEND_URL:-http://127.0.0.1:5178/}"', entrypoint)
        self.assertIn('VITE_GEOVIEW_URL="${VITE_GEOVIEW_URL:-http://127.0.0.1:4174/}"', entrypoint)

    def test_gpu_worker_is_local_and_cpu_keeps_the_existing_validation_path(self):
        standalone = (
            ROOT / "docker" / "standalone" / "start-jiangxi-standalone.sh"
        ).read_text(encoding="utf-8")
        healthcheck = (
            ROOT / "docker" / "standalone" / "healthcheck.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("/tmp/jiangxi-mmseg-worker.sock", standalone)
        self.assertIn('JIANGXI_MMSEG_WORKER_ENABLED="1"', standalone)
        self.assertIn('JIANGXI_MMSEG_WORKER_ENABLED="0"', standalone)
        self.assertIn("--ping", healthcheck)
        self.assertIn("get_model_paths", healthcheck)

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
