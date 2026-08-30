#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import hashlib
import os
import shutil
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

from applications.common.path_global import generate_url
from applications.interface.inference_device import resolve_inference_device

MMSEG_CONDA_ENV = "MMSeg310"
_curr_dir = os.path.dirname(os.path.abspath(__file__))
MMSEG_SCRIPT = os.path.join(_curr_dir, "mmseg_segmentation.py")

JIANGXI_MODEL_ROOT_ENV = "JIANGXI_MMSEG_MODEL_ROOT"
JIANGXI_MODEL_CONFIG_ENV = "JIANGXI_MMSEG_CONFIG_PATH"
JIANGXI_MODEL_CHECKPOINT_ENV = "JIANGXI_MMSEG_CHECKPOINT_PATH"
JIANGXI_MODEL_METADATA_ENV = "JIANGXI_MMSEG_METADATA_PATH"
JIANGXI_MODEL_SOURCE_ENV = "JIANGXI_MMSEG_SOURCE_ROOT"
JIANGXI_MMSEG_WORKER_ENABLED_ENV = "JIANGXI_MMSEG_WORKER_ENABLED"
JIANGXI_MMSEG_WORKER_SOCKET_ENV = "JIANGXI_MMSEG_WORKER_SOCKET"
JIANGXI_CLASS_NAMES = [
    "grassland",
    "forest",
    "building",
    "road",
    "bareground",
    "water",
]


@lru_cache(maxsize=8)
def _file_sha256(path_text: str, size: int, mtime_ns: int) -> str:
    del size, mtime_ns
    digest = hashlib.sha256()
    with open(path_text, "rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified_sha256(path: Path) -> str:
    stat = path.stat()
    return _file_sha256(str(path), stat.st_size, stat.st_mtime_ns)


def _source_tree_sha256(source_root: Path) -> Tuple[str, int]:
    digest = hashlib.sha256()
    files = sorted(
        (path for path in source_root.rglob("*.py") if path.is_file()),
        key=lambda path: path.relative_to(source_root).as_posix(),
    )
    for path in files:
        relative = path.relative_to(source_root).as_posix().encode("utf-8")
        size = path.stat().st_size
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(size.to_bytes(8, "big"))
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest(), len(files)


def _verify_dependency_hashes(model_metadata: dict, source_root: Path) -> None:
    for dependency_name, expected_hash in (model_metadata.get("dependencies") or {}).items():
        candidates = [source_root / dependency_name]
        candidates.extend(source_root.rglob(dependency_name))
        dependency_path = next((path for path in candidates if path.is_file()), None)
        if dependency_path is None:
            raise RuntimeError(f"江西模型依赖权重不存在：{dependency_name}")
        expected = str(expected_hash or "").strip().lower()
        if len(expected) != 64 or _verified_sha256(dependency_path) != expected:
            raise RuntimeError(f"江西模型依赖权重 SHA-256 不匹配：{dependency_name}")


def get_model_paths(model_id: str) -> Tuple[str, str]:
    if model_id == "cc-ln/CUGRS":
        model_root_text = os.environ.get(JIANGXI_MODEL_ROOT_ENV, "").strip()
        config = os.environ.get(JIANGXI_MODEL_CONFIG_ENV, "").strip()
        checkpoint = os.environ.get(JIANGXI_MODEL_CHECKPOINT_ENV, "").strip()
        metadata = os.environ.get(JIANGXI_MODEL_METADATA_ENV, "").strip()
        if not model_root_text or not config or not checkpoint or not metadata:
            raise RuntimeError(
                "江西地物分类模型未配置：请同时设置江西模型根目录、配置、权重和元数据路径"
            )

        model_root = Path(model_root_text).expanduser().resolve()
        asset_paths = [
            Path(config).expanduser().resolve(),
            Path(checkpoint).expanduser().resolve(),
            Path(metadata).expanduser().resolve(),
        ]
        source_root_text = os.environ.get(JIANGXI_MODEL_SOURCE_ENV, "").strip()

        for path in asset_paths:
            try:
                path.relative_to(model_root)
            except ValueError as exc:
                raise RuntimeError(f"江西模型资产必须位于受控目录 {model_root}：{path}") from exc

        config_path, checkpoint_path, metadata_path = asset_paths[:3]
        missing = [
            str(path)
            for path in (config_path, checkpoint_path, metadata_path)
            if not path.is_file()
        ]
        if missing:
            raise RuntimeError("江西地物分类模型文件不存在：" + ", ".join(missing))

        try:
            model_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"江西地物分类模型元数据无效：{exc}") from exc
        if str(model_metadata.get("region", "")).strip().lower() != "jiangxi":
            raise RuntimeError("江西地物分类模型元数据的 region 必须为 jiangxi")
        if model_metadata.get("classes") != JIANGXI_CLASS_NAMES:
            raise RuntimeError(
                "江西地物分类模型六类标签顺序不匹配："
                + ", ".join(JIANGXI_CLASS_NAMES)
            )

        expected_config_hash = str(model_metadata.get("config_sha256", "")).lower()
        expected_checkpoint_hash = str(
            model_metadata.get("checkpoint_sha256", "")
        ).lower()
        if len(expected_config_hash) != 64 or len(expected_checkpoint_hash) != 64:
            raise RuntimeError("江西地物分类模型元数据缺少有效的 SHA-256 绑定")
        if _verified_sha256(config_path) != expected_config_hash:
            raise RuntimeError("江西地物分类模型配置 SHA-256 不匹配")
        if _verified_sha256(checkpoint_path) != expected_checkpoint_hash:
            raise RuntimeError("江西地物分类模型权重 SHA-256 不匹配")

        if not source_root_text:
            raise RuntimeError("江西地物分类模型必须配置受控源码目录")
        source_root = Path(source_root_text).expanduser().resolve()
        try:
            source_root.relative_to(model_root)
        except ValueError as exc:
            raise RuntimeError(
                f"江西模型资产必须位于受控目录 {model_root}：{source_root}"
            ) from exc
        if not source_root.is_dir():
            raise RuntimeError(f"江西地物分类模型源码目录不存在：{source_root}")
        expected_source_hash = str(model_metadata.get("source_sha256", "")).lower()
        try:
            expected_source_count = int(model_metadata.get("source_file_count", 0))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("江西地物分类模型元数据的源码文件数无效") from exc
        if len(expected_source_hash) != 64 or expected_source_count <= 0:
            raise RuntimeError("江西地物分类模型元数据缺少有效的源码 SHA-256 绑定")
        actual_source_hash, actual_source_count = _source_tree_sha256(source_root)
        if actual_source_count != expected_source_count:
            raise RuntimeError("江西地物分类模型源码文件数不匹配")
        if actual_source_hash != expected_source_hash:
            raise RuntimeError("江西地物分类模型源码 SHA-256 不匹配")
        _verify_dependency_hashes(model_metadata, source_root)
        return str(config_path), str(checkpoint_path)
    raise ValueError(f"Unknown MMSeg model: {model_id}")


def _resolve_mmseg_python() -> List[str]:
    configured = os.environ.get("JIANGXI_MMSEG_PYTHON", "").strip()
    candidates = [configured, sys.executable, shutil.which("python") or ""]
    for candidate in candidates:
        if not candidate or not os.path.exists(candidate) and os.path.sep in candidate:
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "import torch, mmseg; print(torch.__version__)"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0:
            return [candidate]
    return ["conda", "run", "-n", MMSEG_CONDA_ENV, "python"]


def _build_mmseg_env() -> dict:
    env = os.environ.copy()
    mmseg_source_root = env.get(JIANGXI_MODEL_SOURCE_ENV, "").strip()
    mmseg_pkg_dir = os.path.join(mmseg_source_root, "mmseg")
    if os.path.isdir(mmseg_pkg_dir):
        old = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{mmseg_source_root}:{old}" if old else mmseg_source_root
    return env


def _format_subprocess_failure(result) -> str:
    detail = "\n".join(
        part.strip()
        for part in (result.stderr, result.stdout)
        if part and part.strip()
    )
    if result.returncode in {-9, 137}:
        diagnosis = (
            "推理进程被系统终止，可能是 CPU 内存不足。"
            "请使用江西专用的轻量 CPU 模型。"
        )
    else:
        diagnosis = "推理子进程异常退出。"
    suffix = f"\n{detail}" if detail else ""
    return (
        f"MMSeg inference failed (exit code {result.returncode}): "
        f"{diagnosis}{suffix}"
    )


def _worker_enabled() -> bool:
    return os.environ.get(JIANGXI_MMSEG_WORKER_ENABLED_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _request_worker_inference(
    *,
    model_id: str,
    data_path: str,
    out_dir: str,
    names: List[str],
    device: str,
    timeout: int,
) -> Dict:
    socket_path = os.environ.get(JIANGXI_MMSEG_WORKER_SOCKET_ENV, "").strip()
    if not socket_path:
        raise RuntimeError("GPU 推理 Worker 不可用：启用后必须配置 Socket 路径")
    if model_id != "cc-ln/CUGRS":
        raise ValueError(f"Unknown MMSeg model: {model_id}")

    from applications.interface.mmseg_worker import WorkerUnavailableError, request_worker

    try:
        response = request_worker(
            socket_path,
            {
                "action": "infer",
                "model_id": model_id,
                "input_dir": os.path.abspath(data_path),
                "output_dir": os.path.abspath(out_dir),
                "file_names": names,
                "device": device,
                "submitted_at": time.time(),
            },
            timeout=float(timeout),
        )
    except WorkerUnavailableError as exc:
        raise RuntimeError(str(exc)) from exc

    if response.get("status") == "error":
        raise RuntimeError(
            "GPU 推理 Worker 失败：" + str(response.get("error") or "未知错误")
        )
    if response.get("status") != "completed":
        raise RuntimeError(f"GPU 推理 Worker 返回未完成状态：{response}")
    return response


def _run_mmseg_inference(
    model_id: str,
    data_path: str,
    out_dir: str,
    names: List[str],
    device: str = "cpu",
    timeout: int = 1200,
) -> Dict:
    if not names:
        return []

    if _worker_enabled():
        return _request_worker_inference(
            model_id=model_id,
            data_path=data_path,
            out_dir=out_dir,
            names=names,
            device=device,
            timeout=timeout,
        )

    runtime = resolve_inference_device(device)
    effective_device = runtime["effective_device"]

    abs_data_path = os.path.abspath(data_path)
    abs_out_dir = os.path.abspath(out_dir)
    config_path, checkpoint_path = get_model_paths(model_id)
    file_names_str = ",".join(names)

    cmd = _resolve_mmseg_python() + [
        MMSEG_SCRIPT,
        "--config",
        config_path,
        "--checkpoint",
        checkpoint_path,
        "--input_dir",
        abs_data_path,
        "--output_dir",
        abs_out_dir,
        "--file_names",
        file_names_str,
        "--device",
        effective_device,
    ]
    print(f"[MMSeg-Caller] cwd={_curr_dir}", file=sys.stderr)
    print(
        f"[MMSeg-Caller] JIANGXI_MMSEG_SOURCE_ROOT="
        f"{os.environ.get(JIANGXI_MODEL_SOURCE_ENV, '')}",
        file=sys.stderr,
    )
    print(f"[MMSeg-Caller] python={' '.join(_resolve_mmseg_python())}", file=sys.stderr)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=_curr_dir,
        env=_build_mmseg_env(),
    )

    if result.returncode != 0:
        raise RuntimeError(_format_subprocess_failure(result))

    output_data = None
    for line in reversed((result.stdout or "").splitlines()):
        s = line.strip()
        if not s.startswith("{"):
            continue
        try:
            output_data = json.loads(s)
            break
        except Exception:
            continue
    if not output_data or output_data.get("status") != "completed":
        raise RuntimeError(f"Inference incomplete: {output_data}")

    return output_data


def call_mmseg_inference(
    model_id: str,
    data_path: str,
    out_dir: str,
    names: List[str],
    device: str = "cpu",
    timeout: int = 1200,
) -> List[str]:
    if not names:
        return []
    output_data = _run_mmseg_inference(
        model_id=model_id,
        data_path=data_path,
        out_dir=out_dir,
        names=names,
        device=device,
        timeout=timeout,
    )
    temps: List[str] = []
    result_map = {res["name"]: res for res in output_data.get("results", [])}
    for name in names:
        base_name = os.path.splitext(name)[0]
        expected_out_name = f"pred_{base_name}.png"
        res = result_map.get(expected_out_name) or result_map.get(name)
        if not res:
            raise RuntimeError(f"No result returned for file: {name} (expected {expected_out_name})")
        if res.get("status") == "success":
            temps.append(generate_url + res["name"])
        else:
            raise RuntimeError(f"Processing failed for {name}: {res.get('message', 'Unknown error')}")
    return temps


def execute_detailed(
    model_id: str,
    data_path: str,
    out_dir: str,
    names: List[str],
    device: str = "cpu",
) -> Dict:
    """Run one MMSeg process for all tiles and retain per-tile failures."""
    if not names:
        return {"status": "completed", "total": 0, "success": 0, "results": []}
    return _run_mmseg_inference(
        model_id=model_id,
        data_path=data_path,
        out_dir=out_dir,
        names=names,
        device=device,
    )


def execute(
    model_id: str,
    data_path: str,
    out_dir: str,
    names: List[str],
    device: str = "cpu",
) -> List[str]:
    return call_mmseg_inference(model_id=model_id, data_path=data_path, out_dir=out_dir, names=names, device=device)


SUPPORTED_MODELS = {
    "cugrs": {
        "model_id": "cc-ln/CUGRS",
        "description": "CUGRS DinoV3+SwinTransformer land cover model",
    }
}

