import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from applications.interface.mmseg_inference_caller import get_model_paths


ROOT = Path(__file__).resolve().parent


class TestJiangxiCpuContract(unittest.TestCase):
    def test_public_analysis_api_forces_cpu_and_exposes_no_gpu_capability(self):
        source = (ROOT / "applications" / "api" / "analysis.py").read_text(
            encoding="utf-8"
        )
        policy_source = (
            ROOT / "applications" / "interface" / "inference_device.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("gpu_capability", source)
        self.assertIn("device='cpu'", source)
        self.assertNotIn("req_json.get('device', 'auto')", source)
        for capability_field in (
            "cuda_available",
            "device_name",
            "device_count",
            "cuda_version",
        ):
            self.assertNotIn(capability_field, policy_source)

    def test_all_jiangxi_inference_entry_points_default_to_cpu(self):
        paths = [
            ROOT / "applications" / "interface" / "semantic_segmentation.py",
            ROOT / "applications" / "interface" / "mmseg_segmentation.py",
            ROOT / "applications" / "interface" / "mmseg_inference_caller.py",
            ROOT / "applications" / "kml_roi" / "service.py",
            ROOT / "kml_roi_infer.py",
            ROOT / "verify_mmseg.py",
        ]
        source = "\n".join(path.read_text(encoding="utf-8") for path in paths)

        self.assertNotIn('device="auto"', source)
        self.assertNotIn('default="auto"', source)
        self.assertNotIn('device="cuda:0"', source)

    def test_mmseg_subprocess_bootstraps_backend_package_root(self):
        source = (
            ROOT / "applications" / "interface" / "mmseg_segmentation.py"
        ).read_text(encoding="utf-8")

        self.assertIn("Path(__file__).resolve().parents[2]", source)
        self.assertIn("sys.path.insert(0, str(backend_root))", source)

    def test_mmseg_requires_explicit_jiangxi_model_assets(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "江西地物分类模型未配置"):
                get_model_paths("cc-ln/CUGRS")

    def test_mmseg_accepts_existing_jiangxi_model_assets(self):
        with TemporaryDirectory() as tmp_dir:
            config = Path(tmp_dir) / "config.py"
            checkpoint = Path(tmp_dir) / "model.pth"
            config.write_text("# jiangxi model\n", encoding="utf-8")
            checkpoint.write_bytes(b"checkpoint")
            with patch.dict(
                os.environ,
                {
                    "JIANGXI_MMSEG_CONFIG_PATH": str(config),
                    "JIANGXI_MMSEG_CHECKPOINT_PATH": str(checkpoint),
                },
                clear=True,
            ):
                self.assertEqual(
                    get_model_paths("cc-ln/CUGRS"),
                    (str(config.resolve()), str(checkpoint.resolve())),
                )


if __name__ == "__main__":
    unittest.main()
