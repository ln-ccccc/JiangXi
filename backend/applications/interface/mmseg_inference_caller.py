#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Tuple

from applications.common.path_global import generate_url

MMSEG_CONDA_ENV = "MMSeg310"
_curr_dir = os.path.dirname(os.path.abspath(__file__))
MMSEG_SCRIPT = os.path.join(_curr_dir, "mmseg_segmentation.py")

CUGRS_CONFIG = {
    "model_id": "cc-ln/CUGRS",
    "config_path": os.path.join(_curr_dir, "..", "..", "model", "mmseg_config", "dinov3_swinV1.py"),
    "checkpoint_path": os.path.join(_curr_dir, "..", "..", "model", "mmseg_config", "model.pth"),
}
MMSEG_SOURCE_ROOT = os.path.join(_curr_dir, "..", "..", "model", "mmseg_config", "dinov3_swinV1")


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
        config = os.path.abspath(CUGRS_CONFIG["config_path"])
        checkpoint = os.path.abspath(CUGRS_CONFIG["checkpoint_path"])
        return config, checkpoint
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
    mmseg_pkg_dir = os.path.join(MMSEG_SOURCE_ROOT, "mmseg")
    if os.path.isdir(mmseg_pkg_dir):
        old = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{MMSEG_SOURCE_ROOT}:{old}" if old else MMSEG_SOURCE_ROOT
    return env


def _run_mmseg_inference(
    model_id: str,
    data_path: str,
    out_dir: str,
    names: List[str],
    device: str = "auto",
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
    print(f"[MMSeg-Caller] MMSEG_SOURCE_ROOT={MMSEG_SOURCE_ROOT}", file=sys.stderr)
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
        raise RuntimeError(f"MMSeg inference failed: {result.stderr or result.stdout}")

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
    device: str = "auto",
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
    device: str = "auto",
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
    device: str = "auto",
) -> List[str]:
    return call_mmseg_inference(model_id=model_id, data_path=data_path, out_dir=out_dir, names=names, device=device)


SUPPORTED_MODELS = {
    "cugrs": {
        "model_id": "cc-ln/CUGRS",
        "description": "CUGRS DinoV3+SwinTransformer land cover model",
    }
}

