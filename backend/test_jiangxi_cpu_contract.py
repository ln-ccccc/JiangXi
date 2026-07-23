import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class TestJiangxiCpuContract(unittest.TestCase):
    def test_public_analysis_api_forces_cpu_and_exposes_no_gpu_capability(self):
        source = (ROOT / "applications" / "api" / "analysis.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("gpu_capability", source)
        self.assertIn("device='cpu'", source)
        self.assertNotIn("req_json.get('device', 'auto')", source)

    def test_all_jiangxi_inference_entry_points_default_to_cpu(self):
        paths = [
            ROOT / "applications" / "interface" / "semantic_segmentation.py",
            ROOT / "applications" / "interface" / "mmseg_segmentation.py",
            ROOT / "applications" / "interface" / "mmseg_inference_caller.py",
            ROOT / "applications" / "kml_roi" / "service.py",
            ROOT / "kml_roi_infer.py",
        ]
        source = "\n".join(path.read_text(encoding="utf-8") for path in paths)

        self.assertNotIn('device="auto"', source)
        self.assertNotIn('default="auto"', source)


if __name__ == "__main__":
    unittest.main()
