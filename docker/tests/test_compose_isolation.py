"""Docker Compose isolation regression tests for the Jiangxi deployment."""

import unittest
from pathlib import Path, PurePosixPath

import yaml


ROOT = Path(__file__).resolve().parents[2]
PROD_PATH = ROOT / "docker-compose.prod.yml"
GPU_PATH = ROOT / "docker-compose.gpu.yml"


def normalize_mount(mount):
    if isinstance(mount, str):
        parts = mount.split(":", 2)
        source = parts[0]
        target = parts[1]
        mount_type = "bind" if source.startswith((".", "/")) else "volume"
        return mount_type, source, target

    source = mount.get("source") or mount.get("src")
    target = mount.get("target") or mount.get("dst") or mount.get("destination")
    mount_type = mount.get("type") or (
        "bind" if source and source.startswith((".", "/")) else "volume"
    )
    return mount_type, source, target


def mount_overlays_backend_model(target):
    target_path = PurePosixPath(target)
    backend_path = PurePosixPath("/app/backend")
    model_path = backend_path / "model"
    covers_backend = target_path == backend_path or target_path in backend_path.parents
    overlaps_model = (
        target_path == model_path
        or target_path in model_path.parents
        or model_path in target_path.parents
    )
    return covers_backend or overlaps_model


class ComposeIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prod_text = PROD_PATH.read_text(encoding="utf-8")
        cls.prod = yaml.safe_load(cls.prod_text)
        cls.gpu = yaml.safe_load(GPU_PATH.read_text(encoding="utf-8"))

    def test_jiangxi_image_and_container_names_are_isolated(self):
        services = self.prod["services"]
        self.assertEqual(services["backend"]["image"], "${APP_IMAGE:-jiangxi-runtime:current}")
        self.assertEqual(
            {name: service["container_name"] for name, service in services.items()},
            {
                "backend": "jiangxi-backend",
                "frontend": "jiangxi-frontend",
                "miner-api": "jiangxi-miner-api",
                "miner-web": "jiangxi-miner-web",
                "mysql": "jiangxi-mysql",
            },
        )

    def test_only_browser_entrypoints_are_published_on_loopback(self):
        services = self.prod["services"]
        self.assertEqual(services["backend"]["ports"], ["127.0.0.1:5178:5008"])
        self.assertEqual(services["frontend"]["ports"], ["127.0.0.1:4174:3000"])
        self.assertEqual(services["miner-web"]["ports"], ["127.0.0.1:4173:4000"])
        self.assertNotIn("ports", services["miner-api"])
        self.assertNotIn("ports", services["mysql"])

    def test_shared_app_environment_uses_jiangxi_auth_and_public_origins(self):
        environment = self.prod["services"]["backend"]["environment"]
        self.assertEqual(environment.get("DB_BACKEND"), "mysql")
        self.assertEqual(environment.get("SESSION_COOKIE_NAME"), "jiangxi_session")
        self.assertEqual(
            environment["CORS_ALLOWED_ORIGINS"],
            "http://127.0.0.1:4173,http://127.0.0.1:4174",
        )
        self.assertEqual(environment["FRONTEND_PORT"], 3000)
        self.assertEqual(environment["MINER_FRONTEND_PORT"], 4000)
        self.assertEqual(environment["VITE_GEOVIEW_URL"], "http://127.0.0.1:4174/")
        self.assertEqual(environment["VUE_APP_MINER_URL"], "http://127.0.0.1:4173/")
        self.assertEqual(environment["VUE_APP_BACKEND_URL"], "http://127.0.0.1:5178/")

    def test_backend_and_miner_api_share_backend_auth_configuration(self):
        services = self.prod["services"]
        shared_keys = {
            "SECRET_KEY",
            "MYSQL_HOST",
            "MYSQL_PORT",
            "MYSQL_USERNAME",
            "MYSQL_PASSWORD",
            "MYSQL_DATABASE",
        }
        for key in shared_keys:
            self.assertEqual(
                services["backend"]["environment"][key],
                services["miner-api"]["environment"][key],
            )
        self.assertEqual(
            services["miner-api"]["environment"]["GEOVIEW_BACKEND_URL"],
            "http://backend:5008",
        )

    def test_named_volumes_are_jiangxi_scoped(self):
        self.assertEqual(
            {name: value["name"] for name, value in self.prod["volumes"].items()},
            {
                "backend-static": "jiangxi_backend_static",
                "mysql-data": "jiangxi_mysql_data",
                "hf-cache": "jiangxi_hf_cache",
                "miner-outputs": "jiangxi_miner_outputs",
                "miner-tiles": "jiangxi_miner_tiles",
            },
        )

    def test_runtime_mounts_preserve_image_model_and_use_jiangxi_data(self):
        services = self.prod["services"]
        backend_mounts = services["backend"]["volumes"]
        miner_api_mounts = services["miner-api"]["volumes"]
        self.assertNotIn("./backend:/app/backend:ro", backend_mounts)
        self.assertIn("./backend/applications:/app/backend/applications:ro", backend_mounts)
        self.assertIn("./backend/app.py:/app/backend/app.py:ro", backend_mounts)
        self.assertIn("./backend/kml_roi_infer.py:/app/backend/kml_roi_infer.py:ro", backend_mounts)
        runtime_mount = "./docker/standalone/runtime_data:/app/runtime_data:ro"
        self.assertIn(runtime_mount, backend_mounts)
        self.assertIn(runtime_mount, miner_api_mounts)
        self.assertNotIn("node_modules", self.prod_text)

    def test_relative_bind_sources_exist_and_no_mount_overlays_backend_model(self):
        for service_name, service in self.prod["services"].items():
            for raw_mount in service.get("volumes", []):
                mount_type, source, target = normalize_mount(raw_mount)
                if mount_type == "bind" and source and not Path(source).is_absolute():
                    self.assertTrue(
                        (ROOT / source).exists(),
                        f"{service_name} bind source does not exist: {source}",
                    )
                self.assertFalse(
                    mount_overlays_backend_model(target),
                    f"{service_name} mount overlays image backend/model: {target}",
                )

    def test_mount_parser_supports_short_and_long_compose_syntax(self):
        self.assertEqual(
            normalize_mount("./backend/app.py:/app/backend/app.py:ro"),
            ("bind", "./backend/app.py", "/app/backend/app.py"),
        )
        self.assertEqual(
            normalize_mount(
                {
                    "type": "bind",
                    "source": "./frontend/public",
                    "target": "/app/frontend/public",
                    "read_only": True,
                }
            ),
            ("bind", "./frontend/public", "/app/frontend/public"),
        )

    def test_runtime_mounts_use_only_existing_jiangxi_workbook_and_frontend_public(self):
        services = self.prod["services"]
        backend_mounts = services["backend"]["volumes"]
        miner_api_mounts = services["miner-api"]["volumes"]
        all_runtime_mounts = backend_mounts + miner_api_mounts
        for workbook_name in (
            "NDVI_2year.xlsx",
            "NDBI_by_fid_2year_avg.xlsx",
            "NDWI_by_fid_2year_avg.xlsx",
            "NDSI_by_fid_2year_avg.xlsx",
        ):
            self.assertFalse(any(workbook_name in mount for mount in all_runtime_mounts))

        authoritative_workbook_mount = "./miner/data:/app/miner/data:ro"
        self.assertIn(authoritative_workbook_mount, backend_mounts)
        self.assertIn(authoritative_workbook_mount, miner_api_mounts)
        self.assertIn(
            "./frontend/public:/app/frontend/public:ro",
            services["frontend"]["volumes"],
        )
        self.assertNotIn("node_modules", self.prod_text)

    def test_active_map_configuration_has_no_dali_or_localhost_fallback(self):
        docker_code = "\n".join(
            [
                (ROOT / "docker" / "generate_miner_tiles.py").read_text(encoding="utf-8"),
                (ROOT / "docker" / "write-runtime-env.py").read_text(encoding="utf-8"),
            ]
        )
        active_runtime = self.prod_text + docker_code
        self.assertNotIn("/offline_maps/dali", active_runtime)
        self.assertNotIn("maps/dali", active_runtime)
        self.assertNotIn("localhost:8000", active_runtime)
        environment = self.prod["services"]["backend"]["environment"]
        self.assertEqual(
            environment["MINER_LOCAL_TILE_URL"],
            "${MINER_LOCAL_TILE_URL:-/tiles/{z}/{x}/{y}.png}",
        )
        self.assertEqual(environment["MINER_TILE_TIF_PATH"], "${MINER_TILE_TIF_PATH:-}")

    def test_mysql_defaults_are_jiangxi_scoped(self):
        app_environment = self.prod["services"]["backend"]["environment"]
        mysql_environment = self.prod["services"]["mysql"]["environment"]
        self.assertEqual(app_environment["MYSQL_USERNAME"], "${MYSQL_USERNAME:-jiangxi}")
        self.assertEqual(app_environment["MYSQL_DATABASE"], "${MYSQL_DATABASE:-jiangxi}")
        self.assertEqual(mysql_environment["MYSQL_USER"], "${MYSQL_USERNAME:-jiangxi}")
        self.assertEqual(mysql_environment["MYSQL_DATABASE"], "${MYSQL_DATABASE:-jiangxi}")

    def test_active_runtime_has_no_yunnan_source_fallback(self):
        analysis_source = (ROOT / "backend" / "applications" / "api" / "analysis.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("yunnan.kml", (self.prod_text + analysis_source).lower())
        self.assertNotIn('"Jiangxi_NaturalMine.kmz"', analysis_source)
        self.assertIn('current_app.config["MINER_DEFAULT_KMZ_PATH"]', analysis_source)

    def test_default_jiangxi_data_paths_are_explicit(self):
        environment = self.prod["services"]["backend"]["environment"]
        self.assertEqual(
            environment["MINER_DEFAULT_KMZ_PATH"],
            "${MINER_DEFAULT_KMZ_PATH:-/app/runtime_data/Jiangxi_NaturalMine.kmz}",
        )
        self.assertEqual(
            environment["MINER_DEFAULT_GEO_SOURCE_PATH"],
            "${MINER_DEFAULT_GEO_SOURCE_PATH:-/app/runtime_data/348个图斑.shp}",
        )
        self.assertEqual(
            environment["MINER_ECOLOGY_WORKBOOK_PATH"],
            "${MINER_ECOLOGY_WORKBOOK_PATH:-/app/miner/data/348图斑_TableMERNet无图像预测结果.xlsx}",
        )

    def test_gpu_overlay_uses_jiangxi_gpu_image_for_compute_services(self):
        services = self.gpu["services"]
        self.assertEqual(services["backend"].get("image"), "jiangxi-runtime:gpu")
        self.assertEqual(services["miner-api"].get("image"), "jiangxi-runtime:gpu")


class EnvironmentExampleTests(unittest.TestCase):
    def test_example_defaults_match_jiangxi_compose_contract(self):
        values = {}
        for raw_line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key] = value

        self.assertEqual(values["APP_IMAGE"], "jiangxi-runtime:current")
        self.assertEqual(values["DB_BACKEND"], "mysql")
        self.assertEqual(values["SESSION_COOKIE_NAME"], "jiangxi_session")
        self.assertEqual(
            values["CORS_ALLOWED_ORIGINS"],
            "http://127.0.0.1:4173,http://127.0.0.1:4174",
        )
        self.assertEqual(values["VITE_GEOVIEW_URL"], "http://127.0.0.1:4174/")
        self.assertEqual(values["VUE_APP_MINER_URL"], "http://127.0.0.1:4173/")
        self.assertEqual(values["VUE_APP_BACKEND_URL"], "http://127.0.0.1:5178/")
        self.assertEqual(values["MYSQL_USERNAME"], "jiangxi")
        self.assertEqual(values["MYSQL_DATABASE"], "jiangxi")


if __name__ == "__main__":
    unittest.main()
