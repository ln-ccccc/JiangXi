#!/usr/bin/env python3
"""KML ROI inference pipeline for large GeoTIFFs."""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from applications.region_source import resolve_default_jiangxi_kmz
from applications.kml_roi.pipeline import run_kml_roi_pipeline
from applications.interface.inference_device import resolve_inference_device


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    backend_root = Path(__file__).resolve().parent
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    parser = argparse.ArgumentParser(description="KML ROI inference and FID outputs")
    parser.add_argument("--old_tif", required=True, help="Path of old GeoTIFF")
    parser.add_argument("--new_tif", required=True, help="Path of new GeoTIFF")
    parser.add_argument(
        "--kml",
        default=str(resolve_default_jiangxi_kmz()),
        help="KML/KMZ path",
    )
    parser.add_argument(
        "--output_root",
        default=os.getenv("MINER_CHANGE_OUTPUT_ROOT") or str(repo_root / "miner" / "change_matrix_outputs"),
        help="Output root path",
    )
    parser.add_argument(
        "--work_dir",
        default=str(backend_root / ".tmp_kml_roi_infer"),
        help="Temporary work directory",
    )
    parser.add_argument("--model_id", default="cc-ln/CUGRS", help="MMSeg model id")
    parser.add_argument(
        "--device",
        default=os.getenv("JIANGXI_INFERENCE_DEVICE", "cpu"),
        choices=["cpu", "cuda", "cuda:0"],
        help="Jiangxi inference device; CPU is the default, GPU must be explicit",
    )
    parser.add_argument("--limit", type=int, default=0, help="Process first N polygons only")
    parser.add_argument("--keep_workdir", action="store_true", help="Keep work directory")
    parser.add_argument("--year", default="", help="Single snapshot year (YYYY). Stores outputs as {FID}+{YYYY}.")
    parser.add_argument("--old_year", default="", help="Old year label (YYYY) for old_tif")
    parser.add_argument("--new_year", default="", help="New year label (YYYY) for new_tif")
    parser.add_argument(
        "--manifest",
        default=os.environ.get("JIANGXI_ASSET_MANIFEST_PATH", ""),
        help="江西 TBBH/map_fid manifest path",
    )
    args = parser.parse_args()

    old_tif = Path(args.old_tif).expanduser().resolve()
    new_tif = Path(args.new_tif).expanduser().resolve()
    kml_path = Path(args.kml).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve()
    if not args.manifest:
        raise RuntimeError("江西推理必须提供资产 manifest，禁止直接使用历史 FID")
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "ok":
        raise RuntimeError("江西资产 manifest 状态不是 ok")
    map_fid_to_tbbh = {
        int(map_fid): str(tbbh).strip()
        for tbbh, map_fid in (manifest.get("mapping", {}).get("tbbh_to_map_fid") or {}).items()
    }
    expected_count = int(os.getenv("JIANGXI_EXPECTED_COUNT", "348"))
    if len(map_fid_to_tbbh) != expected_count:
        raise RuntimeError(
            f"江西资产 manifest 映射数量错误: {len(map_fid_to_tbbh)}，期望 {expected_count}"
        )
    model_metadata_text = os.environ.get("JIANGXI_MMSEG_METADATA_PATH", "").strip()
    if not model_metadata_text:
        raise RuntimeError("江西推理必须配置 JIANGXI_MMSEG_METADATA_PATH")
    model_metadata_path = Path(model_metadata_text).expanduser().resolve()
    if not model_metadata_path.is_file():
        raise RuntimeError(f"江西模型元数据不存在: {model_metadata_path}")
    try:
        model_metadata = json.loads(model_metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"江西模型元数据无法读取: {model_metadata_path}") from exc
    required_model_hashes = ("config_sha256", "checkpoint_sha256", "source_sha256")
    if any(len(str(model_metadata.get(key) or "").strip()) != 64 for key in required_model_hashes):
        raise RuntimeError("江西模型元数据缺少完整模型哈希")
    started_at = time.monotonic()
    runtime = resolve_inference_device(args.device)
    summary = run_kml_roi_pipeline(
        old_tif=old_tif,
        new_tif=new_tif,
        kml_path=kml_path,
        output_root=output_root,
        work_dir=work_dir,
        model_id=args.model_id,
        device=runtime["effective_device"],
        limit=args.limit,
        keep_workdir=args.keep_workdir,
        year=args.year or None,
        old_year=args.old_year or None,
        new_year=args.new_year or None,
    )
    matched_fids = summary.get("matched_fid_list") or []
    unresolved = [fid for fid in matched_fids if int(fid) not in map_fid_to_tbbh]
    if unresolved:
        raise RuntimeError(f"KML 中存在无法映射为 TBBH 的 map_fid: {unresolved[:20]}")
    worker_runtime = summary.pop("inference_runtime", {})
    if isinstance(worker_runtime, dict) and worker_runtime.get("peak_memory_bytes") is not None:
        runtime["peak_memory_bytes"] = worker_runtime["peak_memory_bytes"]
    runtime["duration_seconds"] = round(time.monotonic() - started_at, 3)
    summary["runtime"] = runtime
    written_fids = summary.get("written_fid_list") or []
    model_hashes = {
        key: model_metadata.get(key)
        for key in ("config_sha256", "checkpoint_sha256", "source_sha256")
        if model_metadata.get(key)
    }
    result_manifests = []
    asset_manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    for raw_fid in written_fids:
        map_fid = int(raw_fid)
        tbbh = map_fid_to_tbbh[map_fid]
        result_path = output_root / str(map_fid) / "result_manifest.json"
        result_path.write_text(
            json.dumps(
                {
                    "tbbh": tbbh,
                    "map_fid": map_fid,
                    "source_output_dir": str(map_fid),
                    "model_hashes": model_hashes,
                    "asset_manifest_sha256": asset_manifest_sha256,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        result_manifests.append(str(result_path))
    summary["matched_tbbh_list"] = [map_fid_to_tbbh[int(fid)] for fid in matched_fids]
    summary["written_tbbh_list"] = [map_fid_to_tbbh[int(fid)] for fid in written_fids]
    summary["written_results"] = [
        {
            "tbbh": map_fid_to_tbbh[int(fid)],
            "map_fid": int(fid),
            "source_output_dir": str(int(fid)),
        }
        for fid in written_fids
    ]
    summary["result_manifests"] = result_manifests
    summary.pop("matched_fid_list", None)
    summary.pop("written_fid_list", None)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

