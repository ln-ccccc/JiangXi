#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import hashlib
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

from applications.common.path_global import generate_url

MMSEG_CONDA_ENV = "MMSeg310"
_curr_dir = os.path.dirname(os.path.abspath(__file__))
MMSEG_SCRIPT = os.path.join(_curr_dir, "mmseg_segmentation.py")

JIANGXI_MODEL_ROOT_ENV = "JIANGXI_MMSEG_MODEL_ROOT"
JIANGXI_MODEL_CONFIG_ENV = "JIANGXI_MMSEG_CONFIG_PATH"
JIANGXI_MODEL_CHECKPOINT_ENV = "JIANGXI_MMSEG_CHECKPOINT_PATH"
JIANGXI_MODEL_METADATA_ENV = "JIANGXI_MMSEG_METADATA_PATH"
JIANGXI_MODEL_SOURCE_ENV = "JIANGXI_MMSEG_SOURCE_ROOT"
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


def _patch_mmdet_mmcv_guard() -> None:
    mmdet_init = "/opt/conda/envs/MMSeg310/lib/python3.10/site-packages/mmdet/__init__.py"
    if not os.path.exists(mmdet_init):
        return
    try:
        with open(mmdet_init, "r", encoding="utf-8") as f:
            content = f.read()
        updated = re.sub(
            r"mmcv_maximum_version\s*=\s*(['\"])2\.(1|2)\.0\1",
            "mmcv_maximum_version = '2.3.0'",
            content,
        )
        if updated != content:
            with open(mmdet_init, "w", encoding="utf-8") as f:
                f.write(updated)
    except Exception as e:
        print(f"[MMSeg-Caller] patch mmdet guard failed: {e}", file=sys.stderr)


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
        if source_root_text:
            asset_paths.append(Path(source_root_text).expanduser().resolve())

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

        if source_root_text and not asset_paths[3].is_dir():
            raise RuntimeError(f"江西地物分类模型源码目录不存在：{asset_paths[3]}")
        return str(config_path), str(checkpoint_path)
    raise ValueError(f"Unknown MMSeg model: {model_id}")


def _resolve_mmseg_python() -> List[str]:
    candidate_paths = [
        "/opt/conda/envs/MMSeg310/bin/python",
        "/home/livablecity/miniconda3/envs/MMSeg310/bin/python",
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return [path]
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

    _patch_mmdet_mmcv_guard()

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
        device,
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

