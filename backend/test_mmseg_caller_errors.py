import unittest
from types import SimpleNamespace

from applications.interface.mmseg_inference_caller import _format_subprocess_failure


class TestMmsegCallerErrors(unittest.TestCase):
    def test_sigkill_reports_cpu_memory_diagnosis(self):
        result = SimpleNamespace(
            returncode=-9,
            stderr="[MMSeg] Loading model",
            stdout="",
        )

        message = _format_subprocess_failure(result)

        self.assertIn("exit code -9", message)
        self.assertIn("内存不足", message)
        self.assertIn("[MMSeg] Loading model", message)


if __name__ == "__main__":
    unittest.main()
