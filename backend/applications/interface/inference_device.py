"""Jiangxi inference-device policy shared by all MMSeg entry points."""

from __future__ import annotations

import os
from typing import Dict


DEFAULT_INFERENCE_DEVICE = "cpu"
ALLOWED_INFERENCE_DEVICES = {"cpu", "cuda:0"}


class InvalidInferenceDevice(ValueError):
    """Raised when an API client requests an unsupported device."""


def resolve_inference_device(requested_device: str | None = None) -> Dict[str, object]:
    configured = requested_device
    if configured is None or not str(configured).strip():
        configured = os.getenv("JIANGXI_INFERENCE_DEVICE", DEFAULT_INFERENCE_DEVICE)

    requested = str(configured or DEFAULT_INFERENCE_DEVICE).strip().lower()
    if requested == "cuda":
        requested = "cuda:0"
    if requested not in ALLOWED_INFERENCE_DEVICES:
        raise InvalidInferenceDevice("江西项目 device 仅支持 cpu、cuda:0")

    if requested == "cpu":
        return {
            "requested_device": requested,
            "effective_device": "cpu",
            "cuda_available": False,
            "device_name": None,
            "cuda_version": None,
        }

    try:
        import torch
    except ImportError as exc:
        raise InvalidInferenceDevice("CUDA 不可用：当前 Python 环境未安装 PyTorch") from exc

    if not torch.cuda.is_available() or torch.cuda.device_count() < 1:
        raise InvalidInferenceDevice("CUDA 不可用：未检测到可用 GPU")

    return {
        "requested_device": requested,
        "effective_device": "cuda:0",
        "cuda_available": True,
        "device_name": torch.cuda.get_device_name(0),
        "cuda_version": str(torch.version.cuda or ""),
    }
