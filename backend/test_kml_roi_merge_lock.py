"""2026-09-16 审查 P2-2 回归：KML 增量合并竞态收口。

两个层面：
1. kml_merge.merge_kml_increment 输出改「同目录临时文件 + os.replace」原子写，
   消除并发读者（持锁推理子进程 --kml 侧）读到半截 XML 的窗口；
2. 上传 KML 时的共享 runtime.kml 读-改-写挪进与子进程推理同一持锁区：
   父进程先取 .kml_roi_infer.lock，合并后把锁 fd 传给子进程复用（--lock_fd），
   并发合并不再互相覆盖、子进程读到的必是本次合并结果。

fcntl 相关用例在 Windows 宿主（无 fcntl）自动 skip，权威验证在容器（AGENTS §5）。
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    import fcntl
except ImportError:
    fcntl = None

from applications.kml_roi import service
from applications.kml_roi.kml_merge import merge_kml_increment

LOCK_RELATIVE_PATH = ".kml_roi_infer.lock"


def _write_placemark_kml(path, fids):
    placemarks = "".join(
        f"<Placemark><name>{fid}</name>"
        f"<ExtendedData><SimpleData name=\"fid\">{fid}</SimpleData></ExtendedData>"
        f"<Polygon><outerBoundaryIs><LinearRing><coordinates>"
        f"100.0 25.0 100.1 25.0 100.1 25.1 100.0 25.0"
        f"</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>"
        for fid in fids
    )
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        + placemarks
        + "</Document></kml>",
        encoding="utf-8",
    )
    return path


class MergeAtomicWriteTests(unittest.TestCase):
    def test_merge_atomic_write_replaces_target_without_tmp_leftover(self):
        # P2-2 回归：合并输出不得直接 write 目标文件（半截 XML 窗口），
        # 必须临时文件 + os.replace，且任何路径都不残留 *.tmp
        with tempfile.TemporaryDirectory(prefix="kml-merge-atomic-") as temp_dir:
            root = Path(temp_dir)
            base_kml = _write_placemark_kml(root / "base.kml", ["1"])
            output_kml = root / "runtime.kml"
            output_kml.write_text("STALE-CONTENT-SHOULD-BE-REPLACED", encoding="utf-8")

            incoming_kml = _write_placemark_kml(root / "incoming.kml", ["2"])

            summary = merge_kml_increment(base_kml, incoming_kml, output_kml=output_kml)

            self.assertEqual(summary["inserted"], 1)
            text = output_kml.read_text(encoding="utf-8")
            self.assertIn("<name>2</name>", text)
            self.assertNotIn("STALE-CONTENT", text)
            leftovers = [p.name for p in root.iterdir() if p.name.endswith(".tmp")]
            self.assertEqual(leftovers, [])

            # 连续合并第二遍（模拟下一请求全量重建 runtime.kml）：状态清理正确
            second_incoming = _write_placemark_kml(root / "incoming2.kml", ["3"])
            merge_kml_increment(base_kml, second_incoming, output_kml=output_kml)
            text = output_kml.read_text(encoding="utf-8")
            self.assertIn("<name>3</name>", text)
            self.assertNotIn("<name>2</name>", text)
            leftovers = [p.name for p in root.iterdir() if p.name.endswith(".tmp")]
            self.assertEqual(leftovers, [])


@unittest.skipIf(fcntl is None, "Windows 宿主无 fcntl，锁链路在容器内验证")
class ParentLockMergeTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix="kml-merge-lock-")
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.default_kml = _write_placemark_kml(self.root / "Jiangxi_NaturalMine.kml", ["1"])
        self.upload_kml = _write_placemark_kml(self.root / "upload.kml", ["2"])
        # default 库为 .kml 后缀时 merge_target 即 default 库本身（真实链路只有
        # .kmz 底座才落到 runtime.kml）；断言围绕实际 merge 输出路径。
        self.merged_kml = self.default_kml
        self.tif_path = self.root / "input.tif"
        self.tif_path.write_bytes(b"tif")
        self.manifest_path = self.root / "manifest.json"
        self.manifest_path.write_text(
            json.dumps({"status": "ok", "mapping": {"tbbh_to_map_fid": {}}}),
            encoding="utf-8",
        )
        self.output_root = self.root / "outputs"
        self.lock_path = self.output_root / LOCK_RELATIVE_PATH
        self.captured = []

    def _fake_run(self, command, **kwargs):
        self.captured.append({"command": list(command), "kwargs": kwargs})
        # 合并链路：子进程执行期间父进程锁必须仍被持有（此刻尝试抢锁应失败）
        with open(self.lock_path, "w") as probe:
            try:
                fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                pass
            else:
                fcntl.flock(probe.fileno(), fcntl.LOCK_UN)
                self.fail("子进程运行期间父进程合并锁未持有（持锁区断裂）")
        return SimpleNamespace(returncode=0, stdout='{"status":"completed"}\n', stderr="")

    def _run_inference(self):
        with patch.object(
            service, "resolve_default_jiangxi_kmz", return_value=self.default_kml
        ), patch.object(service, "_run_subprocess_with_cleanup", side_effect=self._fake_run):
            return service.run_kml_roi_inference(
                old_tif_path=str(self.tif_path),
                new_tif_path=str(self.tif_path),
                kml_path=str(self.upload_kml),
                output_root=str(self.output_root),
                manifest_path=str(self.manifest_path),
            )

    def test_upload_merge_holds_parent_lock_and_passes_lock_fd_to_child(self):
        result = self._run_inference()
        self.assertEqual(result["status"], "completed")

        self.assertEqual(len(self.captured), 1)
        command = self.captured[0]["command"]
        self.assertIn("--lock_fd", command)
        lock_fd = int(command[command.index("--lock_fd") + 1])
        pass_fds = self.captured[0]["kwargs"].get("pass_fds")
        self.assertEqual(pass_fds, (lock_fd,))
        self.assertGreaterEqual(lock_fd, 0)

        # 合并确实落盘（.kml 底座场景 merge_target=default 库本身）
        self.assertIn("<name>2</name>", self.merged_kml.read_text(encoding="utf-8"))

        # 调用返回后父进程锁必须已释放（finally 收口），可重新抢占
        with open(self.lock_path, "w") as probe:
            try:
                fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(probe.fileno(), fcntl.LOCK_UN)
            except OSError:
                self.fail("run_kml_roi_inference 返回后合并锁未被释放")

    def test_upload_merge_conflict_raises_busy_valueerror(self):
        # 锁被他人预占时，父进程取锁失败必须转成可读 ValueError
        # （与子进程 busy exit 3 的文案一致），而不是裸 OSError。
        self.output_root.mkdir(parents=True, exist_ok=True)
        blocker = open(self.lock_path, "w")
        fcntl.flock(blocker.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with self.assertRaises(ValueError) as ctx:
                self._run_inference()
            self.assertIn("已有一个图斑推理任务正在执行", str(ctx.exception))
        finally:
            fcntl.flock(blocker.fileno(), fcntl.LOCK_UN)
            blocker.close()
        # 冲突路径不得执行合并（merge 输出文件保持原内容）
        self.assertNotIn("<name>2</name>", self.merged_kml.read_text(encoding="utf-8"))

    def test_default_kml_no_parent_lock_no_lockfd(self):
        # 未上传 KML（使用默认库）时不进入合并链路：不取父锁、不传 --lock_fd，
        # 锁仍由子进程按原语义自行获取（BFF 链路完全不受影响）。
        with patch.object(
            service, "resolve_default_jiangxi_kmz", return_value=self.default_kml
        ), patch.object(service, "_run_subprocess_with_cleanup", side_effect=self._fake_run):
            result = service.run_kml_roi_inference(
                old_tif_path=str(self.tif_path),
                new_tif_path=str(self.tif_path),
                kml_path=str(self.default_kml),
                output_root=str(self.output_root),
                manifest_path=str(self.manifest_path),
            )
        self.assertEqual(result["status"], "completed")
        command = self.captured[0]["command"]
        self.assertNotIn("--lock_fd", command)
        self.assertEqual(self.captured[0]["kwargs"].get("pass_fds"), ())
        # 父锁路径未触发：全程没有创建锁文件
        self.assertFalse(self.lock_path.exists())


@unittest.skipUnless(
    os.name == "nt" and fcntl is None,
    "仅在 fcntl 不可用的宿主验证降级路径",
)
class NoFallbackLockTests(unittest.TestCase):
    def test_parent_lock_unavailable_merges_with_atomic_write_fallback(self):
        # Windows 开发机降级：parent_lock=None，合并照常（原子写兜底），
        # 子进程命令不带 --lock_fd，行为与修复前一致。
        with tempfile.TemporaryDirectory(prefix="kml-merge-fallback-") as temp_dir:
            root = Path(temp_dir)
            default_kml = _write_placemark_kml(root / "Jiangxi_NaturalMine.kml", ["1"])
            upload_kml = _write_placemark_kml(root / "upload.kml", ["2"])
            tif_path = root / "input.tif"
            tif_path.write_bytes(b"tif")
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps({"status": "ok", "mapping": {"tbbh_to_map_fid": {}}}),
                encoding="utf-8",
            )
            output_root = root / "outputs"
            captured = []

            def fake_run(command, **kwargs):
                captured.append({"command": list(command), "kwargs": kwargs})
                return SimpleNamespace(returncode=0, stdout='{"status":"completed"}\n', stderr="")

            with patch.object(
                service, "resolve_default_jiangxi_kmz", return_value=default_kml
            ), patch.object(service, "_run_subprocess_with_cleanup", side_effect=fake_run):
                result = service.run_kml_roi_inference(
                    old_tif_path=str(tif_path),
                    new_tif_path=str(tif_path),
                    kml_path=str(upload_kml),
                    output_root=str(output_root),
                    manifest_path=str(manifest_path),
                )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["kml_update"]["inserted"], 1)
            # .kml 底座场景 merge_target=default 库本身，原子写落盘
            self.assertIn("<name>2</name>", default_kml.read_text(encoding="utf-8"))
            self.assertNotIn("--lock_fd", captured[0]["command"])
            self.assertEqual(captured[0]["kwargs"].get("pass_fds"), ())


if __name__ == "__main__":
    unittest.main()
