import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from applications.interface import mmseg_inference_caller
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

    def test_enabled_worker_is_used_before_model_hash_or_subprocess(self):
        expected = {
            "status": "completed",
            "total": 1,
            "success": 1,
            "results": [{"name": "pred_tile.png", "status": "success"}],
        }
        with patch.dict(
            os.environ,
            {
                "JIANGXI_MMSEG_WORKER_ENABLED": "1",
                "JIANGXI_MMSEG_WORKER_SOCKET": "/tmp/jiangxi-mmseg-test.sock",
            },
        ), patch.object(
            mmseg_inference_caller,
            "_request_worker_inference",
            return_value=expected,
        ) as request_worker, patch.object(
            mmseg_inference_caller,
            "get_model_paths",
        ) as get_model_paths:
            actual = mmseg_inference_caller.execute_detailed(
                model_id="cc-ln/CUGRS",
                data_path="/input",
                out_dir="/output",
                names=["tile.tif"],
                device="cuda:0",
            )

        self.assertEqual(actual, expected)
        request_worker.assert_called_once()
        get_model_paths.assert_not_called()

    def test_enabled_worker_without_socket_fails_clearly(self):
        with patch.dict(
            os.environ,
            {
                "JIANGXI_MMSEG_WORKER_ENABLED": "1",
                "JIANGXI_MMSEG_WORKER_SOCKET": "",
            },
        ):
            with self.assertRaisesRegex(RuntimeError, "GPU 推理 Worker 不可用"):
                mmseg_inference_caller.execute_detailed(
                    model_id="cc-ln/CUGRS",
                    data_path="/input",
                    out_dir="/output",
                    names=["tile.tif"],
                    device="cuda:0",
                )


if __name__ == "__main__":
    unittest.main()
