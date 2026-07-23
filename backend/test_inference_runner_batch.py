import unittest
from unittest.mock import patch

from applications.kml_roi.inference_runner import run_mmseg_tiles


class InferenceRunnerBatchTestCase(unittest.TestCase):
    @patch("applications.interface.mmseg_inference_caller.execute_detailed")
    def test_runs_all_tiles_in_one_model_process_and_keeps_tile_errors(self, execute_detailed):
        execute_detailed.return_value = {
            "results": [
                {"name": "pred_a.png", "status": "success"},
                {"name": "b.tif", "status": "error", "error": "bad tile"},
            ]
        }

        failed, errors, runtime = run_mmseg_tiles(
            model_id="cc-ln/CUGRS",
            data_path="/input",
            out_dir="/output",
            file_names=["a.tif", "b.tif"],
            device="cpu",
        )

        execute_detailed.assert_called_once_with(
            model_id="cc-ln/CUGRS",
            data_path="/input",
            out_dir="/output",
            names=["a.tif", "b.tif"],
            device="cpu",
        )
        self.assertEqual(failed, ["b.tif"])
        self.assertEqual(errors, {"b.tif": "bad tile"})
        self.assertEqual(runtime, {})
