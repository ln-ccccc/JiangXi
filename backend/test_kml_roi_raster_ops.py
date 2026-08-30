import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from applications.kml_roi.raster_ops import draw_polygon_boundary_on_prediction, tif_to_png
from applications.kml_roi.tiles import prepare_tiles


class TestKmlRoiRasterOps(unittest.TestCase):
    def test_tif_to_png_resizes_to_model_size_by_default(self):
        rgb = np.arange(4 * 7 * 3, dtype=np.uint8).reshape(4, 7, 3)
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "tile.png"
            with patch(
                "applications.kml_roi.raster_ops.read_tiff_as_rgb",
                return_value=rgb,
            ), patch(
                "applications.kml_roi.raster_ops.cv2.imwrite",
                return_value=True,
            ) as write_image:
                self.assertTrue(tif_to_png(Path(tmp_dir) / "tile.tif", output_path))

        written = write_image.call_args.args[1]
        self.assertEqual(written.shape, (512, 512, 3))

    def test_tif_to_png_keeps_explicit_native_size(self):
        rgb = np.zeros((4, 7, 3), dtype=np.uint8)
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "preview.png"
            with patch(
                "applications.kml_roi.raster_ops.read_tiff_as_rgb",
                return_value=rgb,
            ), patch(
                "applications.kml_roi.raster_ops.cv2.imwrite",
                return_value=True,
            ) as write_image:
                self.assertTrue(
                    tif_to_png(
                        Path(tmp_dir) / "tile.tif",
                        output_path,
                        resize_to=None,
                    )
                )

        written = write_image.call_args.args[1]
        self.assertEqual(written.shape, (4, 7, 3))
        np.testing.assert_array_equal(written, rgb[:, :, ::-1])

    def test_prepare_tiles_uses_legacy_model_resize(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            features = [("23", {"type": "Polygon", "coordinates": []})]
            with patch(
                "applications.kml_roi.tiles.crop_bbox_from_raster",
                return_value=True,
            ), patch(
                "applications.kml_roi.tiles.tif_to_png",
                return_value=True,
            ) as convert_tile:
                matched, names, variants = prepare_tiles(
                    root / "old.tif",
                    root / "new.tif",
                    features,
                    root / "tiles",
                    year="2026",
                )

        self.assertEqual(matched, ["23"])
        self.assertEqual(names, ["23+2026_tile.png"])
        self.assertEqual(variants["23"][0]["already_cropped"], True)
        self.assertEqual(convert_tile.call_args.kwargs, {})

    def test_roi_boundary_color_is_distinct_from_road_color(self):
        pred_image = np.zeros((4, 4, 3), dtype=np.uint8)
        pred_mask = np.zeros((4, 4), dtype=np.uint8)
        tile_image = np.zeros((4, 4, 3), dtype=np.uint8)
        tile_image[1:3, 1:3] = 10

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "applications.kml_roi.raster_ops.cv2.imread",
                side_effect=[pred_image, pred_mask, tile_image],
            ), patch(
                "applications.kml_roi.raster_ops.cv2.imwrite",
                return_value=True,
            ), patch(
                "applications.kml_roi.raster_ops.cv2.drawContours",
            ) as draw_contours:
                self.assertTrue(
                    draw_polygon_boundary_on_prediction(
                        pred_image_path=root / "pred.png",
                        pred_mask_path=root / "mask.png",
                        tile_image_path=root / "tile.png",
                        out_image_path=root / "out.png",
                        out_mask_path=root / "out_mask.png",
                    )
                )

        self.assertEqual(draw_contours.call_args.args[3], (255, 255, 255))


if __name__ == "__main__":
    unittest.main()
