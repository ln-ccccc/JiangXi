"""P1-1/B1 回归（2026-09-19）：整图 tile 的波段提取与归一化和联动切片路径同源。

修复前整图路径直接取前 3 波段、无归一化：uint16 写出 16 位 PNG（模型输入
数值巨大、预测完全不可信）；4 波段通道序与训练序相反（系统性错乱）；
2 波段 cvtColor 直接崩。联动路径走 read_tiff_as_rgb（extract_rgb_from_multiband
+ 非 uint8 2%/98% 归一化）。现在整图路径复用同一函数与同一公式——
同一图斑两条路径产出字节一致。
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.windows import Window

from applications.common.utils.tiff_processor import (
    extract_rgb_from_multiband,
    normalize_array,
)
from applications.kml_roi.pipeline import (
    _decimated_normalize_params,
    prepare_whole_image_tile,
)


def _write_tif(path: Path, data: np.ndarray, dtype: str) -> Path:
    bands, height, width = data.shape
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
    ) as dst:
        dst.write(data.astype(dtype))
    return path


class WholeImageTileEquivalenceTests(unittest.TestCase):
    def _assert_tile_matches_linked(self, name: str, data: np.ndarray, dtype: str):
        with tempfile.TemporaryDirectory(prefix="kml-whole-tile-") as temp_dir:
            tif = _write_tif(Path(temp_dir) / name, data, dtype)
            # 参照系 = 联动切片路径（read_tiff_as_rgb）的波段提取 + 归一化两步，
            # 与其调用同一对公开函数。第三步白底 nodata 填充是联动路径的
            # nodata 机制；整图路径的 nodata 由 mask/nodata 管线另行剔除
            # （见审查 B2），不在本等价性断言范围内。
            with rasterio.open(tif) as src:
                raw = src.read()
                reference = extract_rgb_from_multiband(
                    np.moveaxis(raw, 0, -1), raw.shape[0]
                )
                if reference.dtype != np.uint8:
                    reference = normalize_array(reference)

                params = _decimated_normalize_params(src)
                tile = prepare_whole_image_tile(
                    src, Window(0, 0, src.width, src.height), params
                )
            self.assertEqual(tile.dtype, np.uint8)
            self.assertEqual(tile.shape, reference.shape)
            np.testing.assert_array_equal(tile, reference)

    def test_uint16_three_band_matches_linked_path(self):
        # 遥感常见 uint16：修复前 16 位 PNG 直写，减 mean 除 std 后数值巨大
        rng = np.random.RandomState(7)
        base = rng.randint(200, 12000, size=(1, 256, 256))
        data = np.concatenate([base, base // 2 + 300, base // 4 + 90], axis=0)
        self._assert_tile_matches_linked("u16.tif", data, "uint16")

    def test_four_band_uint8_channel_order_matches_linked(self):
        # Sentinel-2 式 4 波段：整图路径必须像联动路径一样取 B4/B3/B2
        height, width = 128, 128
        yy, xx = np.mgrid[0:height, 0:width]
        data = np.stack(
            [
                (10 + (xx % 60)).astype(np.uint8),    # B2
                (100 + (yy % 50)).astype(np.uint8),   # B3
                (200 + ((xx + yy) % 40)).astype(np.uint8),  # B4
                np.full((height, width), 77, np.uint8),     # B8
            ]
        )
        self._assert_tile_matches_linked("b4.tif", data, "uint8")

    def test_two_band_does_not_crash_and_matches_linked(self):
        # B1：修复前 cvtColor 对 2 通道抛异常 → 子进程非零退出、无差别失败
        height, width = 96, 96
        yy, xx = np.mgrid[0:height, 0:width]
        data = np.stack(
            [(30 + (xx % 90)).astype(np.uint8), (150 + (yy % 60)).astype(np.uint8)]
        )
        self._assert_tile_matches_linked("b2.tif", data, "uint8")

    def test_single_band_uint8_still_gray_replicated(self):
        height, width = 64, 64
        data = (np.arange(height * width).reshape(1, height, width) % 251).astype(np.uint8)
        self._assert_tile_matches_linked("b1.tif", data, "uint8")


if __name__ == "__main__":
    unittest.main()
