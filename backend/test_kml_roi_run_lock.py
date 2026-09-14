"""复审批次 C：kml_roi_infer.py 跨进程推理互斥锁。"""

import contextlib
import importlib
import io
import json
import tempfile
import unittest
from pathlib import Path

try:
    import fcntl  # noqa: F401

    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False


@unittest.skipUnless(HAS_FCNTL, "flock 仅在 Linux/容器环境可用")
class KmlRoiRunLockTests(unittest.TestCase):
    """Flask subprocess 与 miner BFF execFile 两条链在同一脚本汇合，
    锁必须跨进程串行化推理，占用时输出 status=busy 并以退出码 3 结束。"""

    @classmethod
    def setUpClass(cls):
        # kml_roi_infer.py 是 backend 下的顶层脚本（非包内模块），discover 已把
        # backend 加入 sys.path，可直接导入
        cls.module = importlib.import_module("kml_roi_infer")

    def test_second_acquire_exits_busy_with_json_message(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = self.module._acquire_run_lock(root)
            self.assertIsNotNone(first)
            try:
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    with self.assertRaises(SystemExit) as ctx:
                        self.module._acquire_run_lock(root)
                self.assertEqual(ctx.exception.code, self.module.BUSY_EXIT_CODE)
                payload = json.loads(buffer.getvalue().strip())
                self.assertEqual(payload["status"], "busy")
                self.assertIn("正在执行", payload["error"])
            finally:
                first.close()

            # 释放后可再次获取
            second = self.module._acquire_run_lock(root)
            self.assertIsNotNone(second)
            second.close()


if __name__ == "__main__":
    unittest.main()
