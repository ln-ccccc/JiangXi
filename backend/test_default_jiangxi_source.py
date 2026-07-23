import unittest
from pathlib import Path

from applications.region_source.default_jiangxi_source import (
    DEFAULT_JIANGXI_KMZ_PATH,
    resolve_default_jiangxi_kmz,
)


class TestDefaultJiangxiSource(unittest.TestCase):
    def test_default_path_points_to_authoritative_kmz(self):
        self.assertEqual(
            str(DEFAULT_JIANGXI_KMZ_PATH),
            r"D:\项目\江西数据\Jiangxi_NaturalMine.kmz",
        )

    def test_resolve_default_jiangxi_kmz_prefers_explicit_value(self):
        custom = Path(r"D:\tmp\override.kmz")
        self.assertEqual(resolve_default_jiangxi_kmz(custom), custom)
