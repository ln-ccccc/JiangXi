"""2026-09-16 审查 P2-3 回归：Flask 侧 kml_roi 子进程孤儿收口。

service.py 此前用裸 subprocess.run(timeout=3600)：父进程（Flask worker）被
kill 时子进程不随父消亡，孤儿 kml_roi_infer.py 继续持推理 flock 最长 90 分钟，
期间所有推理请求 400/409。现复用 mmseg_inference_caller._run_subprocess_with_cleanup
的 Popen+finally kill 模式，任何退出路径（超时/上游异常/SystemExit）都杀掉并
回收子进程；POSIX 上子进程独立进程组并以 killpg 整组兜底，Windows 用
TerminateProcess。
"""

import os
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
        # 2841071 超时按影像规模放宽（P1-2 回归钉）：假 tif 元数据不可读 → 14400 兜底
        self.assertEqual(calls[0]["kwargs"].get("timeout"), 14400)
        # 无合并链路（默认库）时无锁 fd 传递
        self.assertEqual(calls[0]["kwargs"].get("pass_fds"), ())

    def test_run_inference_timeout_scales_with_image_size(self):
        # P1-2 回归钉（2841071）：可读影像超时走缩放公式
        # min(14400, max(3600, tiles*2*3))——小影像落 3600 下限
        import numpy as np
        import rasterio as rio
        from rasterio.transform import from_origin

        calls = []

        def fake_cleanup(command, **kwargs):
            calls.append({"kwargs": kwargs})
            return SimpleNamespace(returncode=0, stdout='{"status": "completed"}', stderr="")

        with tempfile.TemporaryDirectory(prefix="kml-timeout-scale-") as temp_dir:
            root = Path(temp_dir)
            kml_path = root / "roi.kml"
            tif_path = root / "input.tif"
            manifest_path = root / "manifest.json"
            kml_path.write_text("<kml />", encoding="utf-8")
            with rio.open(
                tif_path,
                "w",
                driver="GTiff",
                height=512,
                width=512,
                count=1,
                dtype="uint8",
                crs="EPSG:32650",
                transform=from_origin(500000, 4000000, 10, 10),
            ) as dst:
                dst.write(np.zeros((1, 512, 512), dtype=np.uint8))
            manifest_path.write_text(
                '{"status": "ok", "mapping": {"tbbh_to_map_fid": {}}}', encoding="utf-8"
            )

            with patch.object(
                service, "resolve_default_jiangxi_kmz", return_value=kml_path
            ), patch.object(service, "_run_subprocess_with_cleanup", side_effect=fake_cleanup):
                service.run_kml_roi_inference(
                    old_tif_path=str(tif_path),
                    new_tif_path=str(tif_path),
                    output_root=str(root / "outputs"),
                    manifest_path=str(manifest_path),
                )

        self.assertEqual(len(calls), 1)
        # 512×512 → 1 tile → 1*2*3=6 → max(3600, 6) = 3600 下限
        self.assertEqual(calls[0]["kwargs"].get("timeout"), 3600)

    def test_timeout_error_preserves_child_output_tail(self):
        # B5（2026-09-19 审查）：超时不再裸抛 TimeoutExpired（上层只见空错误），
        # 转 RuntimeError 并保留子进程已有输出的尾部
        calls = []

        def timing_out_cleanup(command, **kwargs):
            calls.append(kwargs)
            raise subprocess.TimeoutExpired(
                cmd=list(command), timeout=kwargs.get("timeout"), stderr=b"row 12: inferring tile o1_0\n"
            )

        with tempfile.TemporaryDirectory(prefix="kml-timeout-err-") as temp_dir:
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
            ), patch.object(service, "_run_subprocess_with_cleanup", side_effect=timing_out_cleanup):
                with self.assertRaises(RuntimeError) as ctx:
                    service.run_kml_roi_inference(
                        old_tif_path=str(tif_path),
                        new_tif_path=str(tif_path),
                        output_root=str(root / "outputs"),
                        manifest_path=str(manifest_path),
                    )

        self.assertIn("推理超时", str(ctx.exception))
        self.assertIn("row 12", str(ctx.exception))
        self.assertEqual(calls[0].get("timeout"), 14400)

    def test_timeout_estimate_honors_sec_per_tile_env(self):
        # B5：单片成本可经 KML_ROI_EST_SEC_PER_TILE 调整（CPU 冷启动部署调大）
        import rasterio as rio
        from rasterio.transform import from_origin

        calls = []

        def fake_cleanup(command, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(returncode=0, stdout='{"status": "completed"}', stderr="")

        with tempfile.TemporaryDirectory(prefix="kml-timeout-env-") as temp_dir:
            root = Path(temp_dir)
            kml_path = root / "roi.kml"
            tif_path = root / "input.tif"
            manifest_path = root / "manifest.json"
            kml_path.write_text("<kml />", encoding="utf-8")
            # 25×25 个 512 块 → 625 tiles（SPARSE_OK，只写头部不落数据）
            side = 512 * 25
            with rio.open(
                tif_path, "w", driver="GTiff", height=side, width=side, count=1,
                dtype="uint8", crs="EPSG:32650",
                transform=from_origin(500000, 4000000, 10, 10), SPARSE_OK=True,
            ):
                # 只建头部不落数据：本用例只读元数据估算切片数
                pass
            manifest_path.write_text(
                '{"status": "ok", "mapping": {"tbbh_to_map_fid": {}}}', encoding="utf-8"
            )

            for sec_per_tile, expected in ((None, 3750), ("10", 12500)):
                calls.clear()
                env = {"KML_ROI_EST_SEC_PER_TILE": sec_per_tile} if sec_per_tile else {}
                with patch.dict(os.environ, env), patch.object(
                    service, "resolve_default_jiangxi_kmz", return_value=kml_path
                ), patch.object(service, "_run_subprocess_with_cleanup", side_effect=fake_cleanup):
                    service.run_kml_roi_inference(
                        old_tif_path=str(tif_path),
                        new_tif_path=str(tif_path),
                        output_root=str(root / "outputs"),
                        manifest_path=str(manifest_path),
                    )
                self.assertEqual(calls[0].get("timeout"), expected)


if __name__ == "__main__":
    unittest.main()
