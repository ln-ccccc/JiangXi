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
    def test_auto_prefers_cuda_when_available(self):
        from applications.interface.inference_device import resolve_inference_device

        with patch.dict(sys.modules, {"torch": _fake_torch(True)}):
            runtime = resolve_inference_device("auto")

        self.assertEqual(runtime["requested_device"], "auto")
        self.assertEqual(runtime["effective_device"], "cuda:0")
        self.assertTrue(runtime["cuda_available"])
        self.assertEqual(runtime["device_name"], "RTX test")

    def test_auto_falls_back_to_cpu_with_reason(self):
        from applications.interface.inference_device import resolve_inference_device

        with patch.dict(sys.modules, {"torch": _fake_torch(False)}):
            runtime = resolve_inference_device("auto")

        self.assertEqual(runtime["effective_device"], "cpu")
        self.assertFalse(runtime["cuda_available"])
        self.assertIn("CUDA", runtime["fallback_reason"])

    def test_explicit_cuda_rejects_unavailable_runtime(self):
        from applications.interface.inference_device import InferenceDeviceUnavailable, resolve_inference_device

        with patch.dict(sys.modules, {"torch": _fake_torch(False)}):
            with self.assertRaises(InferenceDeviceUnavailable):
                resolve_inference_device("cuda:0")

    def test_rejects_unknown_device(self):
        from applications.interface.inference_device import InvalidInferenceDevice, resolve_inference_device

        with self.assertRaises(InvalidInferenceDevice):
            resolve_inference_device("cuda:1")

