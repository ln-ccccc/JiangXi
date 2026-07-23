import os
import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from applications.interface.mmseg_inference_caller import get_model_paths
from applications.interface.mmseg_segmentation import _validate_loaded_model_contract


ROOT = Path(__file__).resolve().parent


def source_tree_sha256(source_root: Path):
    digest = hashlib.sha256()
    files = sorted(path for path in source_root.rglob("*.py") if path.is_file())
    for path in files:
        relative = path.relative_to(source_root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest(), len(files)


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
            model_root = Path(tmp_dir) / "jiangxi"
            model_root.mkdir()
            config = model_root / "config.py"
            checkpoint = model_root / "model.pth"
            metadata = model_root / "metadata.json"
            config.write_text("# jiangxi model\n", encoding="utf-8")
            checkpoint.write_bytes(b"checkpoint")
            metadata.write_text(
                '{"region":"jiangxi","classes":["grassland","forest",'
                '"building","road","bareground","water"],'
                f'"config_sha256":"{hashlib.sha256(config.read_bytes()).hexdigest()}",'
                f'"checkpoint_sha256":"{hashlib.sha256(checkpoint.read_bytes()).hexdigest()}"}}',
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "JIANGXI_MMSEG_MODEL_ROOT": str(model_root),
                    "JIANGXI_MMSEG_CONFIG_PATH": str(config),
                    "JIANGXI_MMSEG_CHECKPOINT_PATH": str(checkpoint),
                    "JIANGXI_MMSEG_METADATA_PATH": str(metadata),
                },
                clear=True,
            ):
                self.assertEqual(
                    get_model_paths("cc-ln/CUGRS"),
                    (str(config.resolve()), str(checkpoint.resolve())),
                )

    def test_mmseg_rejects_assets_outside_controlled_jiangxi_root(self):
        with TemporaryDirectory() as tmp_dir:
            model_root = Path(tmp_dir) / "jiangxi"
            outside = Path(tmp_dir) / "other"
            model_root.mkdir()
            outside.mkdir()
            config = outside / "config.py"
            checkpoint = outside / "model.pth"
            metadata = outside / "metadata.json"
            config.write_text("# other model\n", encoding="utf-8")
            checkpoint.write_bytes(b"checkpoint")
            metadata.write_text(
                '{"region":"jiangxi","classes":["grassland","forest",'
                '"building","road","bareground","water"],'
                f'"config_sha256":"{hashlib.sha256(config.read_bytes()).hexdigest()}",'
                f'"checkpoint_sha256":"{hashlib.sha256(checkpoint.read_bytes()).hexdigest()}"}}',
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "JIANGXI_MMSEG_MODEL_ROOT": str(model_root),
                    "JIANGXI_MMSEG_CONFIG_PATH": str(config),
                    "JIANGXI_MMSEG_CHECKPOINT_PATH": str(checkpoint),
                    "JIANGXI_MMSEG_METADATA_PATH": str(metadata),
                },
                clear=True,
            ):
                with self.assertRaisesRegex(RuntimeError, "受控目录"):
                    get_model_paths("cc-ln/CUGRS")

    def test_mmseg_rejects_wrong_class_order(self):
        with TemporaryDirectory() as tmp_dir:
            model_root = Path(tmp_dir) / "jiangxi"
            model_root.mkdir()
            config = model_root / "config.py"
            checkpoint = model_root / "model.pth"
            metadata = model_root / "metadata.json"
            config.write_text("# jiangxi model\n", encoding="utf-8")
            checkpoint.write_bytes(b"checkpoint")
            metadata.write_text(
                '{"region":"jiangxi","classes":["water","forest",'
                '"building","road","bareground","grassland"],'
                f'"config_sha256":"{hashlib.sha256(config.read_bytes()).hexdigest()}",'
                f'"checkpoint_sha256":"{hashlib.sha256(checkpoint.read_bytes()).hexdigest()}"}}',
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "JIANGXI_MMSEG_MODEL_ROOT": str(model_root),
                    "JIANGXI_MMSEG_CONFIG_PATH": str(config),
                    "JIANGXI_MMSEG_CHECKPOINT_PATH": str(checkpoint),
                    "JIANGXI_MMSEG_METADATA_PATH": str(metadata),
                },
                clear=True,
            ):
                with self.assertRaisesRegex(RuntimeError, "六类标签顺序不匹配"):
                    get_model_paths("cc-ln/CUGRS")

    def test_mmseg_rejects_checkpoint_not_bound_to_metadata(self):
        with TemporaryDirectory() as tmp_dir:
            model_root = Path(tmp_dir) / "jiangxi"
            model_root.mkdir()
            config = model_root / "config.py"
            checkpoint = model_root / "model.pth"
            metadata = model_root / "metadata.json"
            config.write_text("# jiangxi model\n", encoding="utf-8")
            checkpoint.write_bytes(b"checkpoint")
            metadata.write_text(
                '{"region":"jiangxi","classes":["grassland","forest",'
                '"building","road","bareground","water"],'
                f'"config_sha256":"{hashlib.sha256(config.read_bytes()).hexdigest()}",'
                f'"checkpoint_sha256":"{hashlib.sha256(b"other").hexdigest()}"}}',
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "JIANGXI_MMSEG_MODEL_ROOT": str(model_root),
                    "JIANGXI_MMSEG_CONFIG_PATH": str(config),
                    "JIANGXI_MMSEG_CHECKPOINT_PATH": str(checkpoint),
                    "JIANGXI_MMSEG_METADATA_PATH": str(metadata),
                },
                clear=True,
            ):
                with self.assertRaisesRegex(RuntimeError, "权重 SHA-256 不匹配"):
                    get_model_paths("cc-ln/CUGRS")

    def test_mmseg_rejects_custom_source_not_bound_to_metadata(self):
        with TemporaryDirectory() as tmp_dir:
            model_root = Path(tmp_dir) / "jiangxi"
            source_root = model_root / "source"
            source_root.mkdir(parents=True)
            source_file = source_root / "custom_backbone.py"
            source_file.write_text("VALUE = 1\n", encoding="utf-8")
            config = model_root / "config.py"
            checkpoint = model_root / "model.pth"
            metadata = model_root / "metadata.json"
            config.write_text("# jiangxi model\n", encoding="utf-8")
            checkpoint.write_bytes(b"checkpoint")
            source_hash, source_count = source_tree_sha256(source_root)
            metadata.write_text(
                '{"region":"jiangxi","classes":["grassland","forest",'
                '"building","road","bareground","water"],'
                f'"config_sha256":"{hashlib.sha256(config.read_bytes()).hexdigest()}",'
                f'"checkpoint_sha256":"{hashlib.sha256(checkpoint.read_bytes()).hexdigest()}",'
                f'"source_sha256":"{source_hash}",'
                f'"source_file_count":{source_count}}}',
                encoding="utf-8",
            )
            environment = {
                "JIANGXI_MMSEG_MODEL_ROOT": str(model_root),
                "JIANGXI_MMSEG_CONFIG_PATH": str(config),
                "JIANGXI_MMSEG_CHECKPOINT_PATH": str(checkpoint),
                "JIANGXI_MMSEG_METADATA_PATH": str(metadata),
                "JIANGXI_MMSEG_SOURCE_ROOT": str(source_root),
            }
            with patch.dict(os.environ, environment, clear=True):
                self.assertEqual(
                    get_model_paths("cc-ln/CUGRS"),
                    (str(config.resolve()), str(checkpoint.resolve())),
                )
                source_file.write_text("VALUE = 2\n", encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "源码 SHA-256 不匹配"):
                    get_model_paths("cc-ln/CUGRS")

    def test_loaded_model_contract_checks_runtime_classes_and_head_count(self):
        valid_model = SimpleNamespace(
            dataset_meta={
                "classes": (
                    "grassland",
                    "forest",
                    "building",
                    "road",
                    "bareground",
                    "water",
                )
            },
            decode_head=SimpleNamespace(num_classes=6),
        )
        _validate_loaded_model_contract(valid_model)

        wrong_classes = SimpleNamespace(
            dataset_meta={"classes": ("water", "forest")},
            decode_head=SimpleNamespace(num_classes=6),
        )
        with self.assertRaisesRegex(RuntimeError, "运行时类别顺序不匹配"):
            _validate_loaded_model_contract(wrong_classes)

        wrong_head = SimpleNamespace(
            dataset_meta=valid_model.dataset_meta,
            decode_head=SimpleNamespace(num_classes=5),
        )
        with self.assertRaisesRegex(RuntimeError, "分类头类别数必须为 6"):
            _validate_loaded_model_contract(wrong_head)


if __name__ == "__main__":
    unittest.main()
