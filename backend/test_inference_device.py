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
    def test_default_device_is_fixed_to_cpu_even_when_cuda_is_available(self):
        from applications.interface.inference_device import resolve_inference_device

        with patch.dict(sys.modules, {"torch": _fake_torch(True)}):
            runtime = resolve_inference_device()

        self.assertEqual(runtime["requested_device"], "cpu")
        self.assertEqual(runtime["effective_device"], "cpu")

    def test_rejects_auto_and_cuda_modes(self):
        from applications.interface.inference_device import InvalidInferenceDevice, resolve_inference_device

        for value in ("auto", "cuda:0"):
            with self.assertRaisesRegex(InvalidInferenceDevice, "江西项目仅支持 CPU"):
                resolve_inference_device(value)

    def test_rejects_unknown_device(self):
        from applications.interface.inference_device import InvalidInferenceDevice, resolve_inference_device

        with self.assertRaises(InvalidInferenceDevice):
            resolve_inference_device("cuda:1")
