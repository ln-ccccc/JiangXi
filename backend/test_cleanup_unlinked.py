"""B6/B7 回归（2026-09-19）：cleanup 的整图（U 前缀）产物防护与清理出口。

- B7：主循环本有 `^U[1-9][0-9]*$` 防护跳过整图产物，但 `--fid` 显式传 U 名
  没有守卫——运维按手册传 U 名会把整图结果当普通 fid 静默清掉。
- B6：整图 U 产物 GB 级/次且无自动清理出口——新增 `--prune-unlinked N`
  按 mtime 仅保留最近 N 个 U 目录。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cleanup_change_outputs as cleanup_main


class FidUnguardedTests(unittest.TestCase):
    def test_fid_with_unlinked_name_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="kml-b7-") as temp_dir:
            root = Path(temp_dir)
            unlinked = root / "U1789839315"
            unlinked.mkdir()
            (unlinked / "result_old_full.tif").write_bytes(b"x")

            with patch.object(
                sys, "argv",
                ["cleanup_change_outputs.py", "--output_root", str(root), "--fid", "U1789839315"],
            ):
                with self.assertRaisesRegex(ValueError, "U 前缀"):
                    cleanup_main.main()

            # 目录原样保留
            self.assertTrue(unlinked.exists())

    def test_fid_normal_name_still_works(self):
        with tempfile.TemporaryDirectory(prefix="kml-b7-ok-") as temp_dir:
            root = Path(temp_dir)
            fid_dir = root / "11192"
            fid_dir.mkdir()
            (fid_dir / "keep.txt").write_bytes(b"x")

            with patch.object(
                sys, "argv",
                ["cleanup_change_outputs.py", "--output_root", str(root), "--fid", "11192"],
            ):
                rc = cleanup_main.main()
            self.assertEqual(rc, 0)
            self.assertTrue(fid_dir.exists())


class PruneUnlinkedTests(unittest.TestCase):
    def _make(self, root, name, mtime):
        d = root / name
        d.mkdir()
        (d / "result_old_full.tif").write_bytes(b"x")
        os.utime(d, (mtime, mtime))
        return d

    def test_prune_keeps_newest_n_unlinked_dirs(self):
        with tempfile.TemporaryDirectory(prefix="kml-b6-") as temp_dir:
            root = Path(temp_dir)
            self._make(root, "U100", 1_000_000)
            self._make(root, "U200", 2_000_000)
            self._make(root, "U300", 3_000_000)
            normal = root / "11192"
            normal.mkdir()

            removed = cleanup_main.prune_unlinked_dirs(root, 1)

            self.assertEqual(removed, 2)
            self.assertFalse((root / "U100").exists())
            self.assertFalse((root / "U200").exists())
            self.assertTrue((root / "U300").exists(), "最新 U 目录应保留")
            self.assertTrue(normal.exists(), "普通 fid 目录不得波及")

    def test_prune_zero_or_disabled_is_noop(self):
        with tempfile.TemporaryDirectory(prefix="kml-b6-0-") as temp_dir:
            root = Path(temp_dir)
            self._make(root, "U100", 1_000_000)
            self.assertEqual(cleanup_main.prune_unlinked_dirs(root, 0), 0)
            self.assertTrue((root / "U100").exists())

    def test_main_wires_prune_unlinked_flag(self):
        with tempfile.TemporaryDirectory(prefix="kml-b6-flag-") as temp_dir:
            root = Path(temp_dir)
            self._make(root, "U100", 1_000_000)
            self._make(root, "U200", 2_000_000)

            with patch.object(
                sys, "argv",
                ["cleanup_change_outputs.py", "--output_root", str(root), "--prune-unlinked", "1"],
            ):
                rc = cleanup_main.main()
            self.assertEqual(rc, 0)
            self.assertTrue((root / "U200").exists())
            self.assertFalse((root / "U100").exists())


if __name__ == "__main__":
    unittest.main()
