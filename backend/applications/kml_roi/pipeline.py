import json
import shutil
import time
from pathlib import Path
from typing import Dict, Optional

from applications.kml_roi.inference_runner import run_mmseg_tiles
from applications.kml_roi.kml import load_kml_features
from applications.kml_roi.raster_ops import raster_union_bounds_4326
from applications.kml_roi.spatial_index import filter_features_by_bounds
from applications.kml_roi.tiles import distribute_outputs, prepare_tiles


def run_kml_roi_pipeline(
    *,
    old_tif: Path,
    new_tif: Path,
    kml_path: Path,
    output_root: Path,
    work_dir: Path,
    model_id: str,
    device: str,
    limit: int = 0,
    keep_workdir: bool = False,
    year: Optional[str] = None,
    old_year: Optional[str] = None,
    new_year: Optional[str] = None,
    linked_fids: Optional[set] = None,
) -> Dict:
    tile_dir = work_dir / "tiles"
    mmseg_out_dir = work_dir / "mmseg_out"

    # 逐阶段耗时：供容量评估与性能归因，随 summary 一并返回
    stage_durations: Dict[str, float] = {}
    stage_started = time.monotonic()
    run_started = stage_started

    def mark(stage: str) -> None:
        nonlocal stage_started
        now = time.monotonic()
        stage_durations[stage] = round(now - stage_started, 3)
        stage_started = now

    if not old_tif.exists() or not new_tif.exists():
        raise FileNotFoundError("old_tif or new_tif does not exist")
    if not kml_path.exists():
        raise FileNotFoundError(f"KML does not exist: {kml_path}")

    if work_dir.exists():
        shutil.rmtree(work_dir)
    tile_dir.mkdir(parents=True, exist_ok=True)
    mmseg_out_dir.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)
    mark("prep_dirs")

    features = load_kml_features(kml_path)
    mark("kml_load")
    bounds_4326 = raster_union_bounds_4326(old_tif, new_tif)
    raw_feature_count = len(features)
    features = filter_features_by_bounds(features, bounds_4326)
    if limit > 0:
        features = features[:limit]
    mark("bounds_filter")

    if linked_fids is not None:
        # 非联动命名空间（2026-09-18 验收反馈）：不在江西清单内的多边形 fid
        # 改写为 U<fid>，产物落 output_root/U<fid>/，与 348 权威目录永不冲突，
        # miner 侧无该身份映射、天然不联动。linked_fids=None 保持原语义。
        features = [
            (fid if fid in linked_fids else "U" + fid, geom)
            for fid, geom in features
        ]

    if not features:
        # 2026-09-18 验收反馈：把无可用图斑的原因说清——多边形存在但全部落在
        # 影像覆盖范围之外，与「KML 本身没有多边形」是两种不同的用户失误。
        if raw_feature_count > 0:
            message = (
                f"KML 共解析到 {raw_feature_count} 个多边形，均未落入影像覆盖范围，"
                "请改用覆盖这些图斑的影像，或更换与影像范围匹配的 KML"
            )
        else:
            message = "KML 中未解析到可用多边形，请检查文件内容"
        return {
            "status": "no_features",
            "message": message,
            "stage_durations": dict(stage_durations),
            "total_seconds": round(time.monotonic() - run_started, 3),
        }

    matched_fids, file_names, variants_by_fid = prepare_tiles(
        old_tif,
        new_tif,
        features,
        tile_dir,
        year=year or None,
        old_year=old_year or None,
        new_year=new_year or None,
    )
    mark("tiles")
    if not matched_fids:
        return {
            "status": "completed",
            "message": "No overlaps between polygons and rasters, all skipped",
            "total_features": len(features),
            "matched_fids": 0,
            "stage_durations": dict(stage_durations),
            "total_seconds": round(time.monotonic() - run_started, 3),
        }

    failed_tiles, tile_errors, inference_runtime = run_mmseg_tiles(
        model_id=model_id,
        data_path=str(tile_dir),
        out_dir=str(mmseg_out_dir),
        file_names=file_names,
        device=device,
    )
    mark("inference")
    dist = distribute_outputs(matched_fids, mmseg_out_dir, output_root, variants_by_fid, tile_dir=tile_dir)
    mark("distribute")
    written_fids = int(dist.get("written_fids", 0) or 0)
    if written_fids == 0:
        run_status = "failed"
    elif failed_tiles or dist.get("missing_fids"):
        run_status = "partial"
    else:
        run_status = "completed"
    summary = {
        "status": run_status,
        "total_features": len(features),
        "matched_fids": len(matched_fids),
        "matched_fid_list": matched_fids,
        "output_root": str(output_root),
        "failed_tiles": failed_tiles,
        "tile_errors": tile_errors,
        "inference_runtime": inference_runtime,
        **dist,
    }

    cleanup_started = time.monotonic()
    if not keep_workdir:
        shutil.rmtree(work_dir, ignore_errors=True)
    stage_durations["cleanup"] = round(time.monotonic() - cleanup_started, 3)
    summary["stage_durations"] = dict(stage_durations)
    summary["total_seconds"] = round(time.monotonic() - run_started, 3)

    # keep JSON-serializable contract explicit for callers
    json.dumps(summary, ensure_ascii=False)
    return summary
