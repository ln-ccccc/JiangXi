"""Focused Jiangxi runtime configuration tests without application imports."""

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "applications" / "configs" / "config.py"
SPEC = importlib.util.spec_from_file_location("jiangxi_runtime_config", MODULE_PATH)
CONFIG_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONFIG_MODULE)


class JiangxiRuntimeConfigTests(unittest.TestCase):
    def test_session_cookie_defaults_are_jiangxi_scoped(self):
        config = CONFIG_MODULE.BaseConfig
        self.assertEqual(getattr(config, "SESSION_COOKIE_NAME", None), "jiangxi_session")
        self.assertEqual(getattr(config, "SESSION_COOKIE_PATH", None), "/")
        self.assertTrue(config.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(config.SESSION_COOKIE_SAMESITE, "Lax")

    def test_cors_defaults_only_list_jiangxi_browser_origins(self):
        self.assertEqual(
            CONFIG_MODULE.BaseConfig.CORS_ALLOWED_ORIGINS,
            "http://127.0.0.1:4173,http://127.0.0.1:4174",
        )

    def test_kml_runtime_root_uses_mounted_jiangxi_data(self):
        self.assertEqual(CONFIG_MODULE.BaseConfig.KML_ROI_KML_ROOT, "/app/runtime_data")

    def test_default_kmz_path_uses_mounted_jiangxi_data(self):
        self.assertEqual(
            getattr(CONFIG_MODULE.BaseConfig, "MINER_DEFAULT_KMZ_PATH", None),
            "/app/runtime_data/Jiangxi_NaturalMine.kmz",
        )


if __name__ == "__main__":
    unittest.main()
