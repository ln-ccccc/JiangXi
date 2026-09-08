import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

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


if __name__ == "__main__":
    unittest.main()
