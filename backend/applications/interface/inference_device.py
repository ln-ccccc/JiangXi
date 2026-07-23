"""Jiangxi CPU-only inference policy shared by all MMSeg entry points."""

from __future__ import annotations

from typing import Dict


ALLOWED_INFERENCE_DEVICES = {"cpu"}


class InvalidInferenceDevice(ValueError):
    """Raised when an API client requests an unsupported device."""


def resolve_inference_device(requested_device: str = "cpu") -> Dict[str, object]:
    requested = str(requested_device or "cpu").strip().lower()
    if requested not in ALLOWED_INFERENCE_DEVICES:
        raise InvalidInferenceDevice("江西项目仅支持 CPU 推理，device 仅支持 cpu")

    return {
        "requested_device": requested,
        "effective_device": "cpu",
    }
