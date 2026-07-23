"""Shared CUDA/CPU selection for all MMSeg inference entry points."""

from __future__ import annotations

from typing import Any, Dict


ALLOWED_INFERENCE_DEVICES = {"auto", "cpu", "cuda:0"}


class InvalidInferenceDevice(ValueError):
    """Raised when an API client requests an unsupported device."""


class InferenceDeviceUnavailable(RuntimeError):
    """Raised when an explicitly requested CUDA device cannot be used."""


def _load_torch():
    try:
        import torch
    except Exception as exc:  # pragma: no cover - depends on runtime image
        return None, f"PyTorch 不可用：{exc}"
    return torch, None


def _runtime_details(torch_module: Any) -> Dict[str, Any]:
    cuda_available = bool(torch_module.cuda.is_available())
    details: Dict[str, Any] = {
        "cuda_available": cuda_available,
        "device_name": None,
        "device_count": 0,
        "total_memory_bytes": None,
        "torch_version": getattr(torch_module, "__version__", None),
        "cuda_version": getattr(getattr(torch_module, "version", None), "cuda", None),
    }
    if not cuda_available:
        return details
    try:
        details["device_count"] = int(torch_module.cuda.device_count())
        if details["device_count"] < 1:
            details["cuda_available"] = False
            return details
        details["device_name"] = str(torch_module.cuda.get_device_name(0))
        details["total_memory_bytes"] = int(torch_module.cuda.get_device_properties(0).total_memory)
    except Exception:
        details["cuda_available"] = False
        details["device_name"] = None
        details["device_count"] = 0
        details["total_memory_bytes"] = None
    return details


def resolve_inference_device(requested_device: str = "auto") -> Dict[str, Any]:
    requested = str(requested_device or "auto").strip().lower()
    if requested not in ALLOWED_INFERENCE_DEVICES:
        raise InvalidInferenceDevice("device 仅支持 auto、cpu 或 cuda:0")

    torch_module, torch_error = _load_torch()
    details = _runtime_details(torch_module) if torch_module else {
        "cuda_available": False,
        "device_name": None,
        "device_count": 0,
        "total_memory_bytes": None,
        "torch_version": None,
        "cuda_version": None,
    }
    cuda_available = bool(details["cuda_available"])
    fallback_reason = None
    if requested == "cpu":
        effective = "cpu"
    elif cuda_available:
        effective = "cuda:0"
    elif requested == "cuda:0":
        reason = torch_error or "容器未获得 CUDA 设备；请使用 --gpus all 启动 GPU 镜像"
        raise InferenceDeviceUnavailable(f"请求 cuda:0 失败：{reason}")
    else:
        effective = "cpu"
        fallback_reason = torch_error or "CUDA 不可用，已自动降级为 CPU"

    return {
        "requested_device": requested,
        "effective_device": effective,
        "fallback_reason": fallback_reason,
        **details,
    }


def get_gpu_capability() -> Dict[str, Any]:
    runtime = resolve_inference_device("auto")
    return {
        **runtime,
        "recommended_device": runtime["effective_device"],
    }
