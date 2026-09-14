import os
import tempfile
import unittest
import weakref
from pathlib import Path
from unittest.mock import patch

import numpy as np

from applications.interface import mmseg_segmentation as mmseg_module
from applications.interface.mmseg_segmentation import run_loaded_model_inference


class _FakeTensor:
    def __init__(self, arr):
        self._arr = arr

    def cpu(self):
        return self

    def numpy(self):
        return self._arr


class _FakeSample:
    def __init__(self, arr):
        self.pred_sem_seg = type("PredSeg", (), {})()
        self.pred_sem_seg.data = [_FakeTensor(arr)]


def _write_tile(path, height, width):
    import cv2

    cv2.imwrite(str(path), np.full((height, width, 3), 128, dtype=np.uint8))


class MmsegBatchingTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.model = object()

    def _fake_inference_fn(self, fail_on_batch=False):
        # 镜像生产语义：单输入返回单个样本，列表输入返回列表
        def inference_fn(model, imgs):
            is_batch = isinstance(imgs, list)
            self.calls.append(len(imgs) if is_batch else 1)
            if fail_on_batch and is_batch and len(imgs) > 1:
                raise RuntimeError("simulate batch OOM")
            samples = [
                _FakeSample(np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8))
                for img in (imgs if is_batch else [imgs])
            ]
            return samples if is_batch else samples[0]

        return inference_fn

    def _run(self, tmp_dir, tiles, inference_fn, batch_env=None):
        old_batch = os.getenv("JIANGXI_MMSEG_BATCH_SIZE")
        if batch_env is None:
            os.environ.pop("JIANGXI_MMSEG_BATCH_SIZE", None)
        else:
            os.environ["JIANGXI_MMSEG_BATCH_SIZE"] = batch_env
        try:
            input_dir = Path(tmp_dir) / "tiles"
            output_dir = Path(tmp_dir) / "out"
            input_dir.mkdir(parents=True)
            for name, (h, w) in tiles:
                _write_tile(input_dir / name, h, w)
            return run_loaded_model_inference(
                model=self.model,
                input_dir=str(input_dir),
                output_dir=str(output_dir),
                file_names=[name for name, _ in tiles],
                device="cpu",
                inference_fn=inference_fn,
            )
        finally:
            if old_batch is None:
                os.environ.pop("JIANGXI_MMSEG_BATCH_SIZE", None)
            else:
                os.environ["JIANGXI_MMSEG_BATCH_SIZE"] = old_batch

    def test_same_size_tiles_are_batched_into_one_forward(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = self._run(
                tmp_dir,
                [("a.tif", (512, 512)), ("b.tif", (512, 512)), ("c.tif", (300, 300))],
                self._fake_inference_fn(),
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["success"], 3)
            self.assertEqual(self.calls, [2, 1])
            out_dir = Path(tmp_dir) / "out"
            self.assertTrue((out_dir / "pred_a.png").exists())
            self.assertTrue((out_dir / "mask_c.png").exists())

    def test_batch_failure_falls_back_to_single_inference(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = self._run(
                tmp_dir,
                [("a.tif", (512, 512)), ("b.tif", (512, 512)), ("c.tif", (512, 512))],
                self._fake_inference_fn(fail_on_batch=True),
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["success"], 3)
            self.assertEqual(self.calls, [3, 1, 1, 1])

    def test_batch_size_env_splits_groups(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = self._run(
                tmp_dir,
                [("a.tif", (512, 512)), ("b.tif", (512, 512)), ("c.tif", (512, 512))],
                self._fake_inference_fn(),
                batch_env="2",
            )
            self.assertEqual(result["success"], 3)
            self.assertEqual(self.calls, [2, 1])

    def test_load_failure_keeps_error_isolation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = Path(tmp_dir) / "tiles"
            output_dir = Path(tmp_dir) / "out"
            input_dir.mkdir(parents=True)
            _write_tile(input_dir / "a.tif", 512, 512)
            result = run_loaded_model_inference(
                model=self.model,
                input_dir=str(input_dir),
                output_dir=str(output_dir),
                file_names=["a.tif", "missing.tif"],
                device="cpu",
                inference_fn=self._fake_inference_fn(),
            )
            self.assertEqual(result["success"], 1)
            self.assertEqual(
                [r for r in result["results"] if r.get("status") == "error"],
                [{"name": "missing.tif", "status": "error", "error": "Failed to load image"}],
            )


class StreamingLoadTests(unittest.TestCase):
    """流式加载回归：chunk 级即时加载，任一时刻驻留的已加载数组数 < 文件总数。"""

    def setUp(self):
        self.model = object()
        self.events = []  # ("load", filename) / ("predict", n_imgs, alive_arrays)
        self.weak_arrays = []

    def _spied_loader(self, raise_for=None):
        real_loader = mmseg_module.load_rs_image_with_gdal

        def loader(img_path, to_float32=True):
            filename = os.path.basename(img_path)
            if raise_for and filename in raise_for:
                raise RuntimeError(raise_for[filename])
            arr = real_loader(img_path, to_float32=to_float32)
            self.events.append(("load", filename))
            # 只持弱引用：模块侧释放后数组即可被回收，用于观测真实驻留数
            if arr is not None:
                self.weak_arrays.append(weakref.ref(arr))
            return arr

        return loader

    def _recording_inference_fn(self, fail_on_batch=False):
        def inference_fn(model, imgs):
            is_batch = isinstance(imgs, list)
            count = len(imgs) if is_batch else 1
            # 与 MmsegBatchingTests 的 fake 一致：先记录再抛，失败的批量尝试也计入
            alive = sum(1 for ref in self.weak_arrays if ref() is not None)
            self.events.append(("predict", count, alive))
            if fail_on_batch and is_batch and count > 1:
                raise RuntimeError("simulate batch OOM")
            samples = [
                _FakeSample(np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8))
                for img in (imgs if is_batch else [imgs])
            ]
            return samples if is_batch else samples[0]

        return inference_fn

    def _run_streaming(self, tmp_dir, tiles, inference_fn, batch_env, extra_file_names=()):
        input_dir = Path(tmp_dir) / "tiles"
        output_dir = Path(tmp_dir) / "out"
        input_dir.mkdir(parents=True)
        for name, (h, w) in tiles:
            _write_tile(input_dir / name, h, w)
        file_names = [name for name, _ in tiles] + list(extra_file_names)
        old_batch = os.environ.get("JIANGXI_MMSEG_BATCH_SIZE")
        os.environ["JIANGXI_MMSEG_BATCH_SIZE"] = batch_env
        try:
            with patch.object(
                mmseg_module, "load_rs_image_with_gdal", self._spied_loader()
            ):
                return run_loaded_model_inference(
                    model=self.model,
                    input_dir=str(input_dir),
                    output_dir=str(output_dir),
                    file_names=file_names,
                    device="cpu",
                    inference_fn=inference_fn,
                )
        finally:
            if old_batch is None:
                os.environ.pop("JIANGXI_MMSEG_BATCH_SIZE", None)
            else:
                os.environ["JIANGXI_MMSEG_BATCH_SIZE"] = old_batch

    def test_images_are_loaded_chunk_by_chunk_not_all_at_once(self):
        tiles = [(f"t{i}.tif", (512, 512)) for i in range(6)]
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = self._run_streaming(
                tmp_dir, tiles, self._recording_inference_fn(), batch_env="2"
            )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["success"], 6)
        load_events = [e for e in self.events if e[0] == "load"]
        predict_events = [e for e in self.events if e[0] == "predict"]
        # 每个文件只加载一次（成功文件不重复加载）
        self.assertEqual([name for _, name in load_events], [name for name, _ in tiles])
        # 任一时刻驻留的已加载数组数 < 文件总数（旧实现首次 predict 前 6 张全驻留）
        for _, _count, alive in predict_events:
            self.assertLess(alive, len(tiles))
        # 首次批量前向前只加载了当前 chunk 的 2 张，而不是全部 6 张
        self.assertEqual(self.events[0], ("load", "t0.tif"))
        self.assertEqual(self.events[1], ("load", "t1.tif"))
        self.assertEqual(self.events[2][0], "predict")
        self.assertEqual(self.events[2][1], 2)
        # 3 个 chunk：加载与批量前向严格交替（load,load,predict) x3
        kinds = [e[0] for e in self.events]
        self.assertEqual(kinds, ["load", "load", "predict"] * 3)

    def test_batch_failure_fallback_does_not_reload_images(self):
        tiles = [(f"t{i}.tif", (512, 512)) for i in range(6)]
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = self._run_streaming(
                tmp_dir, tiles, self._recording_inference_fn(fail_on_batch=True), batch_env="4"
            )
        self.assertEqual(result["success"], 6)
        # 批量失败回退逐张复用已加载数组：加载次数仍等于文件数
        load_events = [e for e in self.events if e[0] == "load"]
        self.assertEqual(len(load_events), len(tiles))
        # 两个 chunk 各自批量失败后退回逐张；任一时刻驻留数组数仍 < 文件总数
        predict_sizes = [e[1:] for e in self.events if e[0] == "predict"]
        self.assertEqual([count for count, _ in predict_sizes], [4, 1, 1, 1, 1, 2, 1, 1])
        for _, alive in predict_sizes:
            self.assertLess(alive, len(tiles))

    def test_multi_shape_multi_file_matches_legacy_semantics(self):
        # 512x512: a,b,d（batch 2 → [a,b],[d]）；300x300: c；missing 打开失败
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = self._run_streaming(
                tmp_dir,
                [
                    ("a.tif", (512, 512)),
                    ("b.tif", (512, 512)),
                    ("c.tif", (300, 300)),
                    ("d.tif", (512, 512)),
                ],
                self._recording_inference_fn(),
                batch_env="2",
                extra_file_names=["missing.tif"],
            )
            out_dir = Path(tmp_dir) / "out"
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["total"], 5)
            self.assertEqual(result["success"], 4)
            self.assertEqual(
                [r for r in result["results"] if r.get("status") == "error"],
                [{"name": "missing.tif", "status": "error", "error": "Failed to load image"}],
            )
            for name in ("pred_a.png", "pred_b.png", "pred_c.png", "pred_d.png"):
                self.assertTrue((out_dir / name).exists(), name)
            self.assertTrue((out_dir / "mask_d.png").exists())
        # 分组与批量子集与旧实现一致：[a,b] -> 2、[d] -> 1、[c] -> 1
        predict_counts = [e[1] for e in self.events if e[0] == "predict"]
        self.assertEqual(predict_counts, [2, 1, 1])

    def test_chunk_phase_load_exception_keeps_error_isolation(self):
        # 探测（元数据）成功但正式加载抛异常：错误记录语义保留
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = Path(tmp_dir) / "tiles"
            output_dir = Path(tmp_dir) / "out"
            input_dir.mkdir(parents=True)
            _write_tile(input_dir / "a.tif", 512, 512)
            _write_tile(input_dir / "b.tif", 512, 512)
            with patch.object(
                mmseg_module,
                "load_rs_image_with_gdal",
                self._spied_loader(raise_for={"b.tif": "read failed at chunk time"}),
            ):
                result = run_loaded_model_inference(
                    model=self.model,
                    input_dir=str(input_dir),
                    output_dir=str(output_dir),
                    file_names=["a.tif", "b.tif"],
                    device="cpu",
                    inference_fn=self._recording_inference_fn(),
                )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["success"], 1)
        self.assertEqual(
            [r for r in result["results"] if r.get("status") == "error"],
            [{"name": "b.tif", "status": "error", "error": "read failed at chunk time"}],
        )


if __name__ == "__main__":
    unittest.main()
