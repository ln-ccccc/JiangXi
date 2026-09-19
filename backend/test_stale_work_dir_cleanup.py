"""S7 回归（2026-09-19）：启动时清扫 /tmp 残留 kml-roi-* 工作目录。

SIGKILL 下 TemporaryDirectory 不会执行清理，单次整图推理残留可达数十 GB；
cleanup_stale_work_dirs 按 mtime 只清超龄（默认 >24h）目录，不影响在跑实例。
"""

import os
import tempfile
import time
import unittest

from applications.kml_roi.service import cleanup_stale_work_dirs


class StaleWorkDirCleanupTests(unittest.TestCase):
    def test_stale_dirs_removed_and_fresh_kept(self):
        with tempfile.TemporaryDirectory(prefix="kml-s7-base-") as base:
            stale_infer = os.path.join(base, "kml-roi-infer-123")
            stale_pre = os.path.join(base, "kml-roi-preprocess-456")
            fresh_infer = os.path.join(base, "kml-roi-infer-789")
            unrelated = os.path.join(base, "unrelated-dir")
            for path in (stale_infer, stale_pre, fresh_infer, unrelated):
                os.makedirs(path)
                os.utime(path, (time.time() - 48 * 3600,) * 2)
            os.utime(fresh_infer, (time.time(),) * 2)

            removed = cleanup_stale_work_dirs(max_age_seconds=24 * 3600, base_dir=base)

            self.assertEqual(removed, 2)
            self.assertFalse(os.path.exists(stale_infer))
            self.assertFalse(os.path.exists(stale_pre))
            self.assertTrue(os.path.exists(fresh_infer), "新鲜目录不得误删")
            self.assertTrue(os.path.exists(unrelated), "无关目录不得波及")

    def test_default_age_keeps_recent_dirs(self):
        with tempfile.TemporaryDirectory(prefix="kml-s7-def-") as base:
            recent = os.path.join(base, "kml-roi-infer-now")
            os.makedirs(recent)
            self.assertEqual(cleanup_stale_work_dirs(base_dir=base), 0)
            self.assertTrue(os.path.exists(recent))


if __name__ == "__main__":
    unittest.main()
