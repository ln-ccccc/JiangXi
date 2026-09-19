"""B8 回归（2026-09-19）：整图流式拼接（_run_whole_image_inference）假推理器单测。

流式拼接此前零单元测试——nodata 剔除、混淆矩阵口径、逐行写入、partial
状态全靠手工回归（P1-1/P1-2 正是这类语义缝隙）。这里用假推理器
（按 file_names 产出常量类别的 pred_/mask_ PNG）钉住四种语义：
全 nodata、两期部分 nodata、失败行、超限早退。

B2/B3 的两处【待验证】语义先钉现状、注释标注目标行为，随修复提交翻转。
"""

import re
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin

from applications.kml_roi import pipeline


def _write_tif(path: Path, data, dtype: str = "uint8") -> Path:
    bands, height, width = data.shape
    sparse = data.size > 100_000_000
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=bands,
        dtype=dtype,
        crs="EPSG:32650",
        transform=from_origin(500000, 4000000, 10, 10),
        SPARSE_OK=sparse,
    ) as dst:
        if not sparse:
            dst.write(data.astype(dtype))
    return path


def _gradient(h, w, lo=40, hi=220):
    rows = np.linspace(lo, hi, h, dtype=np.uint8).reshape(h, 1)
    return np.repeat(rows, w, axis=1)


def _fake_inferencer(class_value=2, fail_rows=()):
    """按 file_names 产出常量类别 pred_/mask_ PNG；fail_rows 行不产出并上报失败。"""

    import cv2

    def fake_run_mmseg_tiles(model_id, data_path, out_dir, file_names, device):
        failed, errors = [], {}
        out_dir = Path(out_dir)
        for name in file_names:
            base = name[:-4] if name.endswith(".png") else name
            m = re.search(r"_tile_[on](\d+)_(\d+)$", base)
            row = int(m.group(1)) if m else -1
            if row in fail_rows:
                failed.append(base)
                errors[base] = "fake inference failure"
                continue
            tile = cv2.imread(str(Path(data_path) / name), cv2.IMREAD_COLOR)
            h, w = tile.shape[:2]
            cv2.imwrite(
                str(out_dir / ("pred_" + base + ".png")),
                np.zeros((h, w, 3), np.uint8),
            )
            cv2.imwrite(
                str(out_dir / ("mask_" + base + ".png")),
                np.full((h, w), class_value, np.uint8),
            )
        return failed, errors, {"fake": 0.0}

    return fake_run_mmseg_tiles


class StreamingStitchTests(unittest.TestCase):
    def _run(self, old_data, new_data, fail_rows=(), class_value=2, dtype="uint8"):
        temp_dir = tempfile.mkdtemp(prefix="kml-stitch-")
        root = Path(temp_dir)
        old_tif = _write_tif(root / "old.tif", old_data, dtype)
        new_tif = _write_tif(root / "new.tif", new_data, dtype)
        stages = {}
        with patch.object(
            pipeline,
            "run_mmseg_tiles",
            side_effect=_fake_inferencer(class_value, fail_rows),
        ):
            summary = pipeline._run_whole_image_inference(
                old_tif=old_tif,
                new_tif=new_tif,
                tile_dir=root / "tiles",
                mmseg_out_dir=root / "mmseg_out",
                output_root=root / "outputs",
                model_id="fake-model",
                device="cpu",
                no_features_message="测试输入",
                mark=lambda stage: stages.setdefault(stage, 0.0),
                stage_durations=stages,
                run_started=time.monotonic(),
            )
        return summary, root

    def _read_mask(self, root, name):
        out_dir = root / "outputs"
        fid_dir = next(out_dir.iterdir())
        with rasterio.open(fid_dir / name) as src:
            return src.read(1)

    def test_over_limit_image_fails_fast_without_inference(self):
        # 40 亿像素防误用上限：元数据即超限 → failed 早退，不启动推理
        huge = 200_000
        data = np.zeros((3, huge * 8, huge * 8), dtype=np.uint8)  # 4e12 像素(仅头部)
        with tempfile.TemporaryDirectory(prefix="kml-cap-") as temp_dir:
            root = Path(temp_dir)
            old_tif = _write_tif(root / "old.tif", data)
            new_tif = _write_tif(root / "new.tif", data)
            called = []

            def exploding_inferencer(*args, **kwargs):
                called.append(1)
                raise AssertionError("超限影像不得进入推理")

            with patch.object(pipeline, "run_mmseg_tiles", side_effect=exploding_inferencer):
                summary = pipeline._run_whole_image_inference(
                    old_tif=old_tif,
                    new_tif=new_tif,
                    tile_dir=root / "tiles",
                    mmseg_out_dir=root / "mmseg_out",
                    output_root=root / "outputs",
                    model_id="fake-model",
                    device="cpu",
                    no_features_message="超限",
                    mark=lambda stage: None,
                    stage_durations={},
                    run_started=time.monotonic(),
                )

        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["written_fids"], 0)
        self.assertEqual(called, [])

    def test_all_nodata_rows_are_excluded_from_mask(self):
        # 两期全黑（RGB=0）：模型输出被 nodata 全量剔除 → mask 全 255、pred 置 0
        black = np.zeros((3, 512, 512), dtype=np.uint8)
        summary, root = self._run(black, black)

        self.assertEqual(summary["status"], "completed")
        mask_old = self._read_mask(root, "mask_old_full.tif")
        mask_new = self._read_mask(root, "mask_new_full.tif")
        self.assertTrue((mask_old == 255).all(), "全 nodata 掩膜应全为 255")
        self.assertTrue((mask_new == 255).all())

    def test_old_period_nodata_is_excluded(self):
        # o 期上半黑边、n 期全有效：mask_old 上半 255；mask_new 在 o 期
        # nodata 区同样置 255（联动语义：混淆矩阵 valid = 两期 mask<6）
        h, w = 1024, 512
        old = np.stack([_gradient(h, w)] * 3)
        old[:, :512, :] = 0
        new = np.stack([_gradient(h, w)] * 3)
        summary, root = self._run(old, new)

        self.assertEqual(summary["status"], "completed")
        mask_old = self._read_mask(root, "mask_old_full.tif")
        mask_new = self._read_mask(root, "mask_new_full.tif")
        self.assertTrue((mask_old[:512] == 255).all(), "o 期黑边应剔除为 255")
        self.assertTrue((mask_old[512:] == 2).all(), "o 期有效区应保留预测类别")
        self.assertTrue((mask_new[:512] == 255).all())
        self.assertTrue((mask_new[512:] == 2).all())

    def test_new_period_nodata_is_currently_not_excluded(self):
        # B2【待验证→实锤】：n 期黑边未联合剔除，误判类别在 n 期复活。
        # 现状钉：mask_new 黑边区仍为预测类别 2。目标行为（随 B2 修复翻转）：
        # mask_new 黑边区应为 255。
        h, w = 1024, 512
        old = np.stack([_gradient(h, w)] * 3)
        new = np.stack([_gradient(h, w)] * 3)
        new[:, 512:, :] = 0
        summary, root = self._run(old, new)

        self.assertEqual(summary["status"], "completed")
        mask_new = self._read_mask(root, "mask_new_full.tif")
        # ——现状断言（B2 修复后翻转为 == 255）——
        self.assertTrue((mask_new[512:] == 2).all())

    def test_failed_row_mask_reads_as_nodata_255(self):
        # B3【已证伪，转回归钉】：报告假设失败行未写入的 GTiff 块读出 0（草地）
        # ——实测 profile 带 nodata=255，GDAL 对未写块返回 255，GIS 统计不会
        # 虚增草地。此处把该行为钉死防回潮（若有人去掉 nodata 声明即红）。
        h, w = 1024, 512
        valid = np.stack([_gradient(h, w)] * 3)
        summary, root = self._run(valid, valid, fail_rows={1})

        self.assertEqual(summary["status"], "partial")
        self.assertTrue(summary["failed_tiles"])
        mask_old = self._read_mask(root, "mask_old_full.tif")
        mask_new = self._read_mask(root, "mask_new_full.tif")
        self.assertTrue((mask_old[:512] == 2).all(), "成功行保留预测类别")
        self.assertTrue((mask_old[512:] == 255).all(), "失败行应为 255 nodata")
        self.assertTrue((mask_new[512:] == 255).all())


if __name__ == "__main__":
    unittest.main()
