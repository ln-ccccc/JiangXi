"""复审批次 C：推理调用方的超时缩放与子进程孤儿安全。"""

import subprocess
import unittest
from unittest import mock

from applications.interface import mmseg_inference_caller as caller


class WorkerTimeoutScalingTests(unittest.TestCase):
    def test_worker_timeout_scales_with_batch_size(self):
        """整批单请求超时按瓦片数缩放，避免全量运行触顶 1200s 后客户端报失败、
        worker 却把结果算完落盘的状态不一致。"""
        captured = {}

        def fake_request(**kwargs):
            captured.update(kwargs)
            return {"status": "completed", "results": []}

        names = [f"{i}.tif" for i in range(1000)]
        with mock.patch.object(caller, "_worker_enabled", return_value=True), \
                mock.patch.object(caller, "_request_worker_inference", side_effect=fake_request):
            caller._run_mmseg_inference("cc-ln/CUGRS", "/input", "/output", names, device="cpu")

        self.assertGreaterEqual(captured["timeout"], 3000.0)
        # 小批量仍保持默认下限
        captured.clear()
        with mock.patch.object(caller, "_worker_enabled", return_value=True), \
                mock.patch.object(caller, "_request_worker_inference", side_effect=fake_request):
            caller._run_mmseg_inference("cc-ln/CUGRS", "/input", "/output", ["a.tif"], device="cpu")
        self.assertGreaterEqual(captured["timeout"], 1200.0)


class SubprocessTimeoutScalingTests(unittest.TestCase):
    def test_subprocess_timeout_scales_with_batch_size(self):
        """B4（2026-09-19 审查）：非 worker（子进程）路径的超时同样按瓦片数
        缩放——此前固定 1200s，CPU + 宽影像一行超限即整行空白横带且无重试，
        与 worker 路径行为不一致。"""
        captured = {}

        def fake_cleanup(cmd, **kwargs):
            captured.update(kwargs)
            return mock.MagicMock(returncode=0, stdout='{"status": "completed"}', stderr="")

        names = [f"{i}.tif" for i in range(1000)]
        with mock.patch.object(caller, "_worker_enabled", return_value=False), \
                mock.patch.object(caller, "_run_subprocess_with_cleanup", side_effect=fake_cleanup):
            caller._run_mmseg_inference("cc-ln/CUGRS", "/input", "/output", names, device="cpu")

        self.assertGreaterEqual(captured["timeout"], 3000.0)
        # 小批量仍保持默认下限
        captured.clear()
        with mock.patch.object(caller, "_worker_enabled", return_value=False), \
                mock.patch.object(caller, "_run_subprocess_with_cleanup", side_effect=fake_cleanup):
            caller._run_mmseg_inference("cc-ln/CUGRS", "/input", "/output", ["a.tif"], device="cpu")
        self.assertGreaterEqual(captured["timeout"], 1200.0)


class SubprocessCleanupTests(unittest.TestCase):
    def _fake_proc(self):
        proc = mock.MagicMock()
        proc.poll.return_value = None
        return proc

    def test_subprocess_killed_when_communicate_raises(self):
        """communicate 抛出任意异常（含上游 SIGTERM 引发的 SystemExit 链）时，
        finally 必须杀掉子进程，避免 mmseg_segmentation.py 孤儿化占 GPU。"""
        proc = self._fake_proc()
        proc.communicate.side_effect = RuntimeError("parent interrupted")
        with mock.patch.object(caller.subprocess, "Popen", return_value=proc):
            with self.assertRaises(RuntimeError):
                caller._run_subprocess_with_cleanup(
                    ["python", "x.py"], timeout=10, cwd=None, env=None
                )
        proc.kill.assert_called_once()

    def test_subprocess_killed_and_reraises_on_timeout(self):
        proc = self._fake_proc()
        proc.communicate.side_effect = subprocess.TimeoutExpired(cmd=["python", "x.py"], timeout=10)
        with mock.patch.object(caller.subprocess, "Popen", return_value=proc):
            with self.assertRaises(subprocess.TimeoutExpired):
                caller._run_subprocess_with_cleanup(
                    ["python", "x.py"], timeout=10, cwd=None, env=None
                )
        proc.kill.assert_called_once()

    def test_subprocess_returns_completed_process_on_success(self):
        proc = self._fake_proc()
        proc.communicate.return_value = ("out", "err")
        proc.poll.return_value = 0  # 成功路径进程已退出，finally 不应再 kill
        proc.returncode = 0
        with mock.patch.object(caller.subprocess, "Popen", return_value=proc):
            result = caller._run_subprocess_with_cleanup(
                ["python", "x.py"], timeout=10, cwd=None, env=None
            )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "out")
        self.assertEqual(result.stderr, "err")
        proc.kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
