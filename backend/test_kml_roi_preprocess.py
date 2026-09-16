import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np
import rasterio
from rasterio.transform import from_origin

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from applications import create_app
from applications.extensions import db
from applications.kml_roi import preprocess as preprocess_module
from applications.kml_roi import service


def _file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _make_source_tif(directory, name):
    """带 CRS/transform 的 4 波段合成影像。

    值取近高斯分布并铺满 64x80：既避免 read_tiff_as_rgb 的纯黑背景启发式把
    整图刷成常量，又保证 CLAHE 的局部直方图一定会改写像素。
    """
    path = Path(directory) / name
    height, width = 64, 80
    rng = np.random.RandomState(42)
    base = np.clip(rng.normal(0.5, 0.15, size=(height, width)), 0.03, 0.97) * 1000.0
    data = np.stack(
        [base, base * 0.6 + 80, base * 0.3 + 40, base * 0.8 + 20]
    ).astype(np.float32)
    transform = from_origin(100.0, 21.0, 0.5, 0.5)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=4,
        dtype="float32",
        transform=transform,
        crs="EPSG:4326",
    ) as dst:
        dst.write(data)
    return path


class PreprocessTifAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="kml-roi-preprocess-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.tif = _make_source_tif(self.tmp, "source.tif")

    def test_zero_steps_return_original_and_touch_nothing(self):
        base_dir = Path(self.tmp) / "preprocess"
        result = preprocess_module.preprocess_tif_for_inference(
            self.tif, base_dir, prehandle=0, denoise=0
        )
        self.assertEqual(result, self.tif)
        self.assertFalse(base_dir.exists())

    def test_clahe_product_keeps_georef_and_changes_pixels(self):
        original_digest = _file_sha256(self.tif)
        base_dir = Path(self.tmp) / "clahe"
        product = preprocess_module.preprocess_tif_for_inference(
            self.tif, base_dir, prehandle=2
        )
        self.assertTrue(product.is_file())
        self.assertEqual(product.parent, base_dir)

        with rasterio.open(self.tif) as src, rasterio.open(product) as out:
            self.assertEqual(str(out.crs), "EPSG:4326")
            self.assertEqual(out.transform, src.transform)
            self.assertEqual((out.width, out.height), (src.width, src.height))
            self.assertEqual(out.count, 3)
            self.assertEqual(out.dtypes[0], "uint8")
            original_rgb = preprocess_module.read_tiff_as_rgb(str(self.tif))
            product_rgb = np.dstack([out.read(i) for i in (1, 2, 3)])
        self.assertFalse(np.array_equal(original_rgb, product_rgb))
        # 原文件绝对不动
        self.assertEqual(_file_sha256(self.tif), original_digest)

    def test_median_denoise_product_is_georeferenced(self):
        base_dir = Path(self.tmp) / "median"
        product = preprocess_module.preprocess_tif_for_inference(
            self.tif, base_dir, prehandle=0, denoise=3
        )
        self.assertTrue(product.is_file())
        with rasterio.open(product) as out:
            self.assertEqual(str(out.crs), "EPSG:4326")
            self.assertEqual(out.count, 3)
            self.assertEqual(out.dtypes[0], "uint8")

    def test_both_steps_chain_in_order(self):
        calls = []
        real_handle = preprocess_module.handle

        def spy_handle(fun_type, imgs, src_dir, save_dir, prefix=""):
            calls.append(fun_type)
            return real_handle(fun_type, imgs, src_dir, save_dir, prefix)

        with patch.object(preprocess_module, "handle", side_effect=spy_handle):
            product = preprocess_module.preprocess_tif_for_inference(
                self.tif, Path(self.tmp) / "chain", prehandle=4, denoise=5
            )
        self.assertEqual(calls, [4, 5])
        self.assertTrue(product.is_file())


class ServicePreprocessWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="kml-roi-preprocess-service-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.old_tif = _make_source_tif(self.tmp, "old.tif")
        self.new_tif = _make_source_tif(self.tmp, "new.tif")
        self.kml_path = Path(self.tmp) / "roi.kml"
        self.kml_path.write_text("<kml />", encoding="utf-8")
        self.manifest_path = Path(self.tmp) / "manifest.json"
        self.manifest_path.write_text(
            json.dumps({"status": "ok", "mapping": {"tbbh_to_map_fid": {}}}),
            encoding="utf-8",
        )
        self.output_root = Path(self.tmp) / "outputs"

    def _run_service(self, **overrides):
        commands = []

        def fake_run(command, **kwargs):
            commands.append(list(command))
            return SimpleNamespace(returncode=0, stdout='{"status":"completed"}\n', stderr="")

        kwargs = dict(
            old_tif_path=str(self.old_tif),
            new_tif_path=str(self.new_tif),
            output_root=str(self.output_root),
            manifest_path=str(self.manifest_path),
            device="cpu",
        )
        kwargs.update(overrides)
        with patch.object(
            service, "resolve_default_jiangxi_kmz", return_value=self.kml_path
        ), patch.object(service, "_run_subprocess_with_cleanup", side_effect=fake_run):
            service.run_kml_roi_inference(**kwargs)
        return commands

    @staticmethod
    def _cmd_value(command, flag):
        return Path(command[command.index(flag) + 1])

    def test_default_steps_never_call_handle_and_use_original_inputs(self):
        old_digest, new_digest = _file_sha256(self.old_tif), _file_sha256(self.new_tif)
        with patch.object(preprocess_module, "handle") as mock_handle:
            commands = self._run_service()
        mock_handle.assert_not_called()
        self.assertEqual(len(commands), 1)
        self.assertEqual(self._cmd_value(commands[0], "--old_tif"), self.old_tif)
        self.assertEqual(self._cmd_value(commands[0], "--new_tif"), self.new_tif)
        self.assertEqual(_file_sha256(self.old_tif), old_digest)
        self.assertEqual(_file_sha256(self.new_tif), new_digest)

    def test_preprocessed_products_become_tiling_inputs(self):
        old_digest, new_digest = _file_sha256(self.old_tif), _file_sha256(self.new_tif)
        fun_types = []

        def fake_handle(fun_type, imgs, src_dir, save_dir):
            fun_types.append(fun_type)
            names = []
            for name in imgs:
                arr = np.full((64, 80, 3), 30 * fun_type, dtype=np.uint8)
                new_name = f"fake_{fun_type}_{name}"
                self.assertTrue(cv2.imwrite(os.path.join(save_dir, new_name), arr))
                names.append(new_name)
            return names

        with patch.object(preprocess_module, "handle", side_effect=fake_handle):
            commands = self._run_service(prehandle=2, denoise=3)

        # 两期 × 两个步骤，且按 prehandle → denoise 顺序串联
        self.assertEqual(fun_types, [2, 3, 2, 3])
        command = commands[0]
        old_input = self._cmd_value(command, "--old_tif")
        new_input = self._cmd_value(command, "--new_tif")
        self.assertNotEqual(old_input, self.old_tif)
        self.assertNotEqual(new_input, self.new_tif)
        # 产物位于独立于 work_dir 的预处理临时目录（kml-roi-preprocess-*）。
        # 子进程 pipeline.py 启动时会 rmtree(work_dir) 清空工作目录防残留，
        # 预处理产物若写在 work_dir 内会被吞掉（2026-09-14 真实推理暴露）。
        work_dir = self._cmd_value(command, "--work_dir")
        self.assertTrue(old_input.parents[1].name.startswith("kml-roi-preprocess-"))
        self.assertTrue(new_input.parents[1].name.startswith("kml-roi-preprocess-"))
        self.assertFalse(old_input.is_relative_to(work_dir))
        self.assertFalse(new_input.is_relative_to(work_dir))
        # 原文件绝对不动
        self.assertEqual(_file_sha256(self.old_tif), old_digest)
        self.assertEqual(_file_sha256(self.new_tif), new_digest)

    def test_same_file_inputs_are_preprocessed_once(self):
        fun_types = []

        def fake_handle(fun_type, imgs, src_dir, save_dir):
            fun_types.append(fun_type)
            names = []
            for name in imgs:
                arr = np.full((64, 80, 3), 60 * fun_type, dtype=np.uint8)
                new_name = f"fake_{fun_type}_{name}"
                self.assertTrue(cv2.imwrite(os.path.join(save_dir, new_name), arr))
                names.append(new_name)
            return names

        with patch.object(preprocess_module, "handle", side_effect=fake_handle):
            commands = self._run_service(
                old_tif_path=str(self.old_tif),
                new_tif_path=str(self.old_tif),
                prehandle=2,
            )
        self.assertEqual(fun_types, [2])
        command = commands[0]
        self.assertEqual(
            self._cmd_value(command, "--old_tif"), self._cmd_value(command, "--new_tif")
        )


class PreprocessSizeGuardTests(unittest.TestCase):
    """2026-09-16 审查 P2-5 回归：超阈值输入在整图读内存之前以 ValueError 拒绝。

    预处理在 Flask 请求线程内经 read_tiff_as_rgb 整图读内存（两份全图副本 +
    全尺寸 PNG 往返）。超 MAX_TIFF_SIZE_MB 的输入必须在触碰内存/磁盘前拒绝，
    由端点 except ValueError 映射 400 明确报错。
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="kml-roi-preprocess-size-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.tif = Path(self.tmp) / "small.tif"
        self.tif.write_bytes(b"tiny tif bytes")
        self.base_dir = Path(self.tmp) / "pre"

    def test_oversized_input_rejected_before_memory_or_disk_touch(self):
        # 阈值 patch 为 0 使小文件即超限（免造 500MB 真文件）：
        # 断言 ValueError 报文明确，且未创建任何预处理目录（拒绝发生在最前）
        with patch.object(preprocess_module, "MAX_TIFF_SIZE_MB", 0):
            with self.assertRaises(ValueError) as ctx:
                preprocess_module.preprocess_tif_for_inference(
                    self.tif, self.base_dir, prehandle=2, denoise=3
                )
        self.assertIn("超过上限", str(ctx.exception))
        self.assertIn("预处理输入影像过大", str(ctx.exception))
        self.assertFalse(self.base_dir.exists())

    def test_zero_steps_skip_size_check_entirely(self):
        # prehandle=denoise=0 默认路径零行为变化：不检查尺寸、不触碰文件系统
        with patch.object(preprocess_module, "MAX_TIFF_SIZE_MB", 0):
            result = preprocess_module.preprocess_tif_for_inference(
                self.tif, self.base_dir, prehandle=0, denoise=0
            )
        self.assertEqual(result, self.tif)
        self.assertFalse(self.base_dir.exists())

    def test_size_threshold_reuses_read_tiff_as_rgb_limit(self):
        # 阈值沿用 read_tiff_as_rgb 的 MAX_TIFF_SIZE_MB（单一来源，无第二常量）
        from applications.common.utils import tiff_processor

        self.assertEqual(preprocess_module.MAX_TIFF_SIZE_MB, tiff_processor.MAX_TIFF_SIZE_MB)


class KmlRoiPreprocessApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app.config["PROPAGATE_EXCEPTIONS"] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.input_root = Path(tempfile.mkdtemp(prefix="roi-pre-input-"))
        self.kml_root = Path(tempfile.mkdtemp(prefix="roi-pre-kml-"))
        (self.input_root / "old.tif").write_bytes(b"tif")
        (self.kml_root / "roi.kml").write_text("<kml></kml>", encoding="utf-8")
        self.app.config["KML_ROI_INPUT_ROOT"] = str(self.input_root)
        self.app.config["KML_ROI_KML_ROOT"] = str(self.kml_root)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        shutil.rmtree(self.input_root, ignore_errors=True)
        shutil.rmtree(self.kml_root, ignore_errors=True)

    def sync_admin(self, password="Secret123!"):
        os.environ["ADMIN_USERNAME"] = "admin"
        os.environ["ADMIN_PASSWORD"] = password
        self.app.config["ADMIN_USERNAME"] = "admin"
        self.app.config["ADMIN_PASSWORD"] = password
        from applications.auth.service import sync_admin_from_env

        return sync_admin_from_env()

    def login_as_admin(self, password="Secret123!"):
        self.sync_admin(password)
        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": password},
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_out_of_domain_params_rejected_with_400(self):
        self.login_as_admin()
        with patch("applications.api.analysis.run_kml_roi_inference") as run_inference:
            for payload in (
                {"old_tif_path": "old.tif", "prehandle": 7},
                {"old_tif_path": "old.tif", "prehandle": 1},
                {"old_tif_path": "old.tif", "denoise": 4},
                {"old_tif_path": "old.tif", "denoise": 2},
                {"old_tif_path": "old.tif", "prehandle": "abc"},
                {"old_tif_path": "old.tif", "denoise": [3]},
            ):
                with self.subTest(payload=payload):
                    resp = self.client.post("/api/analysis/kml_roi_inference", json=payload)
                    self.assertEqual(resp.status_code, 400)
            run_inference.assert_not_called()

    def test_valid_params_passed_through_to_service(self):
        self.login_as_admin()
        with patch("applications.api.analysis.run_kml_roi_inference") as run_inference:
            run_inference.return_value = {"ok": True}

            resp = self.client.post(
                "/api/analysis/kml_roi_inference",
                json={
                    "old_tif_path": "old.tif",
                    "kml_path": "roi.kml",
                    "prehandle": 2,
                    "denoise": 3,
                },
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(run_inference.call_args.kwargs["prehandle"], 2)
            self.assertEqual(run_inference.call_args.kwargs["denoise"], 3)

            run_inference.reset_mock()
            run_inference.return_value = {"ok": True}
            resp = self.client.post(
                "/api/analysis/kml_roi_inference",
                json={
                    "old_tif_path": "old.tif",
                    "kml_path": "roi.kml",
                    "prehandle": 4,
                    "denoise": 5,
                },
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(run_inference.call_args.kwargs["prehandle"], 4)
            self.assertEqual(run_inference.call_args.kwargs["denoise"], 5)

    def test_missing_params_default_to_zero(self):
        self.login_as_admin()
        with patch("applications.api.analysis.run_kml_roi_inference") as run_inference:
            run_inference.return_value = {"ok": True}
            resp = self.client.post(
                "/api/analysis/kml_roi_inference",
                json={"old_tif_path": "old.tif", "kml_path": "roi.kml"},
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(run_inference.call_args.kwargs["prehandle"], 0)
            self.assertEqual(run_inference.call_args.kwargs["denoise"], 0)


if __name__ == "__main__":
    unittest.main()
