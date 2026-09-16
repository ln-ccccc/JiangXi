"""2026-09-16 审查 P2-3 回归：Flask 侧 kml_roi 子进程孤儿收口。

service.py 此前用裸 subprocess.run(timeout=3600)：父进程（Flask worker）被
kill 时子进程不随父消亡，孤儿 kml_roi_infer.py 继续持推理 flock 最长 90 分钟，
期间所有推理请求 400/409。现复用 mmseg_inference_caller._run_subprocess_with_cleanup
的 Popen+finally kill 模式，任何退出路径（超时/上游异常/SystemExit）都杀掉并
回收子进程；POSIX 上子进程独立进程组并以 killpg 整组兜底，Windows 用
TerminateProcess。
"""

import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from applications.kml_roi import service

HEARTBEAT_SCRIPT = (
    "import sys, time\n"
    "path = sys.argv[1]\n"
    "with open(path, 'a', encoding='utf-8') as fh:\n"
    "    for _ in range(600):\n"
    "        fh.write('tick\\n')\n"
    "        fh.flush()\n"
    "        time.sleep(0.1)\n"
)


class SubprocessCleanupTests(unittest.TestCase):
    def test_timed_out_inference_child_is_killed_not_orphaned(self):
        # P2-3 回归：超时路径必须杀掉子进程（心跳停止），不得留下孤儿继续跑
        with tempfile.TemporaryDirectory(prefix="kml-cleanup-") as temp_dir:
            heartbeat = Path(temp_dir) / "heartbeat.txt"
            cmd = [sys.executable, "-c", HEARTBEAT_SCRIPT, str(heartbeat)]

            with self.assertRaises(subprocess.TimeoutExpired):
                service._run_subprocess_with_cleanup(cmd, timeout=2, cwd=str(temp_dir))

            ticks_at_kill = heartbeat.read_text(encoding="utf-8").count("tick")
            time.sleep(1.2)
            ticks_after = heartbeat.read_text(encoding="utf-8").count("tick")
            self.assertEqual(
                ticks_after,
                ticks_at_kill,
                "超时后子进程仍存活（孤儿）：心跳在收口后继续增长",
            )

    def test_cleanup_runner_returns_output_and_exit_code(self):
        # 正常路径与 CompletedProcess 等价：stdout/returncode 透传，供上层解析
        with tempfile.TemporaryDirectory(prefix="kml-cleanup-ok-") as temp_dir:
            cmd = [sys.executable, "-c", "print('{\"status\":\"completed\"}')"]
            run_res = service._run_subprocess_with_cleanup(
                cmd, timeout=30, cwd=str(temp_dir)
            )
            self.assertEqual(run_res.returncode, 0)
            self.assertIn('"status":"completed"', run_res.stdout)

    def test_run_inference_routes_through_cleanup_runner_and_maps_busy_exit(self):
        # 接线：run_kml_roi_inference 必须经 _run_subprocess_with_cleanup
        # （孤儿收口）而非裸 subprocess.run；退出码 3 映射为业务 ValueError
        calls = []

        def fake_cleanup(command, **kwargs):
            calls.append({"command": list(command), "kwargs": kwargs})
            return SimpleNamespace(returncode=3, stdout="", stderr="")

        with tempfile.TemporaryDirectory(prefix="kml-cleanup-busy-") as temp_dir:
            root = Path(temp_dir)
            kml_path = root / "roi.kml"
            tif_path = root / "input.tif"
            manifest_path = root / "manifest.json"
            kml_path.write_text("<kml />", encoding="utf-8")
            tif_path.write_bytes(b"tif")
            manifest_path.write_text(
                '{"status": "ok", "mapping": {"tbbh_to_map_fid": {}}}', encoding="utf-8"
            )

            with patch.object(
                service, "resolve_default_jiangxi_kmz", return_value=kml_path
            ), patch.object(service, "_run_subprocess_with_cleanup", side_effect=fake_cleanup):
                with self.assertRaises(ValueError) as ctx:
                    service.run_kml_roi_inference(
                        old_tif_path=str(tif_path),
                        new_tif_path=str(tif_path),
                        output_root=str(root / "outputs"),
                        manifest_path=str(manifest_path),
                    )

        self.assertIn("已有一个图斑推理任务正在执行", str(ctx.exception))
        self.assertEqual(len(calls), 1)
        self.assertIn("--work_dir", calls[0]["command"])
        self.assertEqual(calls[0]["kwargs"].get("timeout"), 3600)
        # 无合并链路（默认库）时无锁 fd 传递
        self.assertEqual(calls[0]["kwargs"].get("pass_fds"), ())


if __name__ == "__main__":
    unittest.main()
