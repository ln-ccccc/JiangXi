"""2026-09-16 审查 P2-4 回归：cleanup 保留集必须含同 fid `_vN` 变体产物。

F1 修复（同 fid 多 Placemark）产出 `{fid}+{YYYY}_v2` / `{fid}_{old|new}_v2`
的第二图斑结果，而 parse_year("2024_v2") 返回 None，这些文件不进
scan_year_masks 的保留集——cleanup_change_outputs.py 按既有手册跑会静默
删掉它们。修复：cleanup_output_dir 的 keep 集补 `_variant_keep_names`，
年命名变体跟随其年份进/出保留集；scan_year_masks 保持纯年份语义，
统计链（变化矩阵/分类占比）行为零变化。
"""

import tempfile
import unittest
from pathlib import Path

from applications.kml_roi.tiles import cleanup_output_dir, scan_year_masks

STAT_FILES = {
    "change_matrix_pixels.csv",
    "change_matrix_percent_rownorm.csv",
    "class_ratio_percent.json",
}


def _touch(fid_dir, name):
    path = fid_dir / name
    path.write_bytes(b"x")
    return path


def _year_triple(fid_dir, fid, year, variant=""):
    stem = f"{fid}+{year}{variant}"
    return [
        _touch(fid_dir, f"{stem}.png"),
        _touch(fid_dir, f"{stem}_mask.png"),
        _touch(fid_dir, f"{stem}_src.png"),
    ]


class CleanupVariantTests(unittest.TestCase):
    def test_cleanup_keeps_same_fid_variant_outputs_for_kept_year(self):
        # P2-4 主回归：保留年份内的 _v2 变体（F1 第二图斑）不得被误删
        with tempfile.TemporaryDirectory(prefix="kml-cleanup-v2-") as temp_dir:
            fid_dir = Path(temp_dir)
            fid = "11192"
            _year_triple(fid_dir, fid, "2023")
            _year_triple(fid_dir, fid, "2024")
            _year_triple(fid_dir, fid, "2024", "_v2")
            for stat in STAT_FILES:
                _touch(fid_dir, stat)

            removed = cleanup_output_dir(fid, fid_dir, keep_last_years=1)

            for stem in (f"{fid}+2024", f"{fid}+2024_v2"):
                for suffix in (".png", "_mask.png", "_src.png"):
                    self.assertTrue((fid_dir / f"{stem}{suffix}").is_file(), f"{stem}{suffix}")
            for suffix in (".png", "_mask.png", "_src.png"):
                self.assertFalse((fid_dir / f"{fid}+2023{suffix}").exists())
            for stat in STAT_FILES:
                self.assertTrue((fid_dir / stat).is_file())
            self.assertEqual(removed, 3)

    def test_cleanup_drops_expired_year_variant_with_base_year(self):
        # 变体跟随基础年份淘汰：被淘汰年份的 _v2 产物一并清理
        with tempfile.TemporaryDirectory(prefix="kml-cleanup-exp-") as temp_dir:
            fid_dir = Path(temp_dir)
            fid = "11192"
            _year_triple(fid_dir, fid, "2023")
            _year_triple(fid_dir, fid, "2023", "_v2")
            _year_triple(fid_dir, fid, "2024")

            cleanup_output_dir(fid, fid_dir, keep_last_years=1)

            self.assertTrue((fid_dir / f"{fid}+2024.png").is_file())
            for suffix in (".png", "_mask.png", "_src.png"):
                self.assertFalse((fid_dir / f"{fid}+2023_v2{suffix}").exists())

    def test_cleanup_keeps_old_new_naming_variants_without_years(self):
        # 无年命名产物（else 分支）：old/new 基础四件 + _vN 变体 + 统计文件保留
        with tempfile.TemporaryDirectory(prefix="kml-cleanup-on-") as temp_dir:
            fid_dir = Path(temp_dir)
            fid = "11192"
            for suffix in (".png", "_mask.png"):
                _touch(fid_dir, f"{fid}_old{suffix}")
                _touch(fid_dir, f"{fid}_new{suffix}")
            for tag in ("old", "new"):
                for suffix in (".png", "_mask.png", "_src.png"):
                    _touch(fid_dir, f"{fid}_{tag}_v2{suffix}")
            for stat in STAT_FILES:
                _touch(fid_dir, stat)
            _touch(fid_dir, f"{fid}_old_v9.png")

            removed = cleanup_output_dir(fid, fid_dir, keep_last_years=3)

            for tag in ("old", "new"):
                for suffix in (".png", "_mask.png", "_src.png"):
                    self.assertTrue(
                        (fid_dir / f"{fid}_{tag}_v2{suffix}").is_file(),
                        f"{fid}_{tag}_v2{suffix}",
                    )
            self.assertFalse((fid_dir / f"{fid}_old_v9.png").exists())
            self.assertEqual(removed, 1)

    def test_cleanup_does_not_protect_unrecognized_files(self):
        # 防过度保护：无法解析为年份/变体形态的文件仍按垃圾清理
        with tempfile.TemporaryDirectory(prefix="kml-cleanup-guard-") as temp_dir:
            fid_dir = Path(temp_dir)
            fid = "11192"
            _year_triple(fid_dir, fid, "2024")
            _touch(fid_dir, f"{fid}+random_mask.png")
            _touch(fid_dir, f"{fid}+2024_vX_mask.png")
            _touch(fid_dir, f"{fid}+20245_v2_mask.png")
            for stat in STAT_FILES:
                _touch(fid_dir, stat)

            cleanup_output_dir(fid, fid_dir, keep_last_years=3)

            self.assertFalse((fid_dir / f"{fid}+random_mask.png").exists())
            self.assertFalse((fid_dir / f"{fid}+2024_vX_mask.png").exists())
            self.assertFalse((fid_dir / f"{fid}+20245_v2_mask.png").exists())
            self.assertTrue((fid_dir / f"{fid}+2024.png").is_file())

    def test_scan_year_masks_stays_pure_year_semantics(self):
        # 统计链零变化的锚：scan_year_masks 仍只收纯年份条目，"2024_v2" 不进
        with tempfile.TemporaryDirectory(prefix="kml-cleanup-scan-") as temp_dir:
            fid_dir = Path(temp_dir)
            fid = "11192"
            _year_triple(fid_dir, fid, "2023")
            _year_triple(fid_dir, fid, "2024")
            _year_triple(fid_dir, fid, "2024", "_v2")

            year_masks = scan_year_masks(fid, fid_dir)

            self.assertEqual([y for y, _, _ in year_masks], [2023, 2024])
            self.assertTrue(all("_v" not in mask.name for _, _, mask in year_masks))


if __name__ == "__main__":
    unittest.main()
