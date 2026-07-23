import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from applications.kml_roi.pipeline import run_kml_roi_pipeline


class TestKmlRoiStatus(unittest.TestCase):
    def test_all_failed_tiles_return_failed_status(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            old_tif = root / "old.tif"
            new_tif = root / "new.tif"
            kml_path = root / "roi.kml"
            old_tif.write_bytes(b"tif")
            new_tif.write_bytes(b"tif")
            kml_path.write_text("<kml></kml>", encoding="utf-8")

            with patch(
                "applications.kml_roi.pipeline.load_kml_features",
                return_value=[("23", {})],
            ), patch(
                "applications.kml_roi.pipeline.raster_union_bounds_4326",
                return_value=(0, 0, 1, 1),
            ), patch(
                "applications.kml_roi.pipeline.filter_features_by_bounds",
                return_value=[("23", {})],
            ), patch(
                "applications.kml_roi.pipeline.prepare_tiles",
                return_value=(["23"], ["23+2026_tile.png"], {"23": [{}]}),
            ), patch(
                "applications.kml_roi.pipeline.run_mmseg_tiles",
                return_value=(
                    ["23+2026_tile.png"],
                    {"23+2026_tile.png": "model missing"},
                    {},
                ),
            ), patch(
                "applications.kml_roi.pipeline.distribute_outputs",
                return_value={
                    "written_fids": 0,
                    "written_fid_list": [],
                    "missing_fids": ["23"],
                },
            ):
                result = run_kml_roi_pipeline(
                    old_tif=old_tif,
                    new_tif=new_tif,
                    kml_path=kml_path,
                    output_root=root / "outputs",
                    work_dir=root / "work",
                    model_id="cc-ln/CUGRS",
                    device="cpu",
                    year="2026",
                )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["written_fids"], 0)


if __name__ == "__main__":
    unittest.main()
