import sys
import types
import unittest
from unittest.mock import patch


class _FakeProperties:
    total_memory = 8 * 1024 * 1024 * 1024


class _FakeCuda:
    def __init__(self, available):
        self.available = available

    def is_available(self):
        return self.available

    def device_count(self):
        return 1 if self.available else 0

    def get_device_name(self, index):
        return "RTX test"

    def get_device_properties(self, index):
        return _FakeProperties()


def _fake_torch(available):
    return types.SimpleNamespace(__version__="2.7.0", version=types.SimpleNamespace(cuda="12.8"), cuda=_FakeCuda(available))


class InferenceDeviceTestCase(unittest.TestCase):
    def test_default_device_remains_cpu_when_no_gpu_profile_is_configured(self):
        from applications.interface.inference_device import resolve_inference_device

        with patch.dict(sys.modules, {"torch": _fake_torch(True)}), patch.dict(
            "os.environ", {}, clear=True
        ):
            runtime = resolve_inference_device()

        self.assertEqual(runtime["requested_device"], "cpu")
        self.assertEqual(runtime["effective_device"], "cpu")

    def test_explicit_cuda_device_is_accepted_when_cuda_is_available(self):
        from applications.interface.inference_device import resolve_inference_device

        with patch.dict(sys.modules, {"torch": _fake_torch(True)}):
            runtime = resolve_inference_device("cuda:0")

        self.assertEqual(runtime["requested_device"], "cuda:0")
        self.assertEqual(runtime["effective_device"], "cuda:0")
        self.assertEqual(runtime["device_name"], "RTX test")
        self.assertEqual(runtime["cuda_version"], "12.8")

    def test_environment_selects_cuda_for_default_resolution(self):
        from applications.interface.inference_device import resolve_inference_device

        with patch.dict(sys.modules, {"torch": _fake_torch(True)}), patch.dict(
            "os.environ", {"JIANGXI_INFERENCE_DEVICE": "cuda:0"}, clear=True
        ):
            runtime = resolve_inference_device()

        self.assertEqual(runtime["effective_device"], "cuda:0")

    def test_rejects_cuda_when_runtime_has_no_cuda(self):
        from applications.interface.inference_device import InvalidInferenceDevice, resolve_inference_device

        with patch.dict(sys.modules, {"torch": _fake_torch(False)}):
            with self.assertRaisesRegex(InvalidInferenceDevice, "CUDA 不可用"):
                resolve_inference_device("cuda:0")

    def test_rejects_auto_and_unsupported_cuda_modes(self):
        from applications.interface.inference_device import InvalidInferenceDevice, resolve_inference_device

        for value in ("auto", "cuda:1"):
            with self.assertRaisesRegex(InvalidInferenceDevice, "仅支持 cpu、cuda:0"):
                resolve_inference_device(value)
