import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "applications" / "region_source" / "default_jiangxi_source.py"
SPEC = importlib.util.spec_from_file_location("default_jiangxi_source", MODULE_PATH)
SOURCE_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE_MODULE)
DEFAULT_JIANGXI_KMZ_PATH = SOURCE_MODULE.DEFAULT_JIANGXI_KMZ_PATH
resolve_default_jiangxi_kmz = SOURCE_MODULE.resolve_default_jiangxi_kmz


class TestDefaultJiangxiSource(unittest.TestCase):
    def test_default_path_points_to_authoritative_kmz(self):
        self.assertEqual(
            DEFAULT_JIANGXI_KMZ_PATH.as_posix(),
            "/app/runtime_data/Jiangxi_NaturalMine.kmz",
        )

    def test_resolve_default_jiangxi_kmz_prefers_explicit_value(self):
        custom = Path(r"D:\tmp\override.kmz")
        self.assertEqual(resolve_default_jiangxi_kmz(custom), custom)
