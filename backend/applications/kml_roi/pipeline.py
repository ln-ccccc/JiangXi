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


def _run_whole_image_inference(
    *,
    old_tif: Path,
    new_tif: Path,
    tile_dir: Path,
    mmseg_out_dir: Path,
    output_root: Path,
    model_id: str,
    device: str,
    no_features_message: str,
    mark,
    stage_durations: Dict,
    run_started: float,
) -> Dict:
    """整图推理：512×512 网格切片 → 逐片推理 → 拼接全图 → U 命名空间落盘。"""
    import cv2
    import numpy as np
    import rasterio
    from applications.kml_roi.change_matrix import write_change_matrix_csv

    fid = "U" + str(int(time.time()))
    tile_size = 512
    tile_dir.mkdir(parents=True, exist_ok=True)
    mmseg_out_dir.mkdir(parents=True, exist_ok=True)
    mark("prep_dirs")

    file_names = []
    grid = []
    with rasterio.open(old_tif) as src:
        height, width = src.height, src.width
    max_pixels = 36_000_000
    if height * width > max_pixels:
        return {
            "status": "failed",
            "message": (
                f"影像尺寸 {width}x{height} 超出整图推理上限"
                f"（约 {max_pixels // 1_000_000}00 万像素），请裁剪或降采样后重试"
            ),
            "total_features": 0,
            "matched_fids": 0,
            "matched_fid_list": [],
            "output_root": str(output_root),
            "failed_tiles": ["whole_image"],
            "tile_errors": {"whole_image": "影像尺寸超限"},
            "inference_runtime": {},
            "written_fids": 0,
            "written_fid_list": [],
            "missing_fids": [],
            "stage_durations": dict(stage_durations),
            "total_seconds": round(time.monotonic() - run_started, 3),
        }
    n_rows = (height + tile_size - 1) // tile_size
    n_cols = (width + tile_size - 1) // tile_size

    for year_tag, tif_path in (("o", old_tif), ("n", new_tif)):
        with rasterio.open(tif_path) as src:
            for r in range(n_rows):
                for c in range(n_cols):
                    win = rasterio.windows.Window(c * tile_size, r * tile_size, tile_size, tile_size)
                    data = src.read(window=win, boundless=True, fill_value=0)
                    arr = np.moveaxis(data, 0, -1)
                    if arr.shape[2] > 3:
                        arr = arr[:, :, :3]
                    elif arr.shape[2] == 1:
                        arr = np.repeat(arr, 3, axis=2)
                    png = tile_dir / (fid + "_tile_" + year_tag + str(r) + "_" + str(c) + ".png")
                    cv2.imwrite(str(png), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
                    if year_tag == "o":
                        valid_h = min(tile_size, height - r * tile_size)
                        valid_w = min(tile_size, width - c * tile_size)
                        grid.append((r, c, valid_h, valid_w))
                    file_names.append(png.name)
    mark("tiles")

    failed_tiles, tile_errors, inference_runtime = run_mmseg_tiles(
        model_id=model_id,
        data_path=str(tile_dir),
        out_dir=str(mmseg_out_dir),
        file_names=file_names,
        device=device,
    )
    mark("inference")

    def stitch(stage, tag, keep_color, missing_fill=None):
        # pred_* 为彩色叠加图（3 通道 BGR），必须全彩拼接；mask_* 为类别索引灰度图
        # missing_fill：切片缺失时该区域填充值（掩膜填 255=无效，混淆矩阵自动剔除）
        channels = 3 if keep_color else 1
        canvas = (
            np.full((height, width, channels), missing_fill or 0, dtype=np.uint8)
            if keep_color
            else np.full((height, width), missing_fill or 0, dtype=np.uint8)
        )
        ok = 0
        for r, c, h, w in grid:
            path = mmseg_out_dir / (stage + "_" + fid + "_tile_" + tag + str(r) + "_" + str(c) + ".png")
            if not path.exists():
                if missing_fill is not None:
                    ok += 0  # 缺失片计入失败统计
                continue
            tile = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            if tile is None:
                continue
            if tile.ndim == 3 and not keep_color:
                tile = tile[:, :, 0]
            if keep_color and tile.ndim == 2:
                tile = cv2.cvtColor(tile, cv2.COLOR_GRAY2BGR)
            canvas[r * tile_size : r * tile_size + h, c * tile_size : c * tile_size + w] = tile[:h, :w]
            ok += 1
        return canvas, ok

    total_tiles = len(grid)
    old_pred, ok_o = stitch("pred", "o", True)
    new_pred, ok_n = stitch("pred", "n", True)
    old_mask, _ = stitch("mask", "o", False, missing_fill=255)
    new_mask, _ = stitch("mask", "n", False, missing_fill=255)
    # o 期原始瓦片就在 tile_dir（无 stage 前缀），拼接为原始影像 _src.png
    src_img = np.zeros((height, width, 3), dtype=np.uint8)
    ok_src = 0
    for r, c, h, w in grid:
        tp = tile_dir / (fid + "_tile_o" + str(r) + "_" + str(c) + ".png")
        if tp.exists():
            tile = cv2.imread(str(tp), cv2.IMREAD_COLOR)
            if tile is not None:
                src_img[r * tile_size : r * tile_size + h, c * tile_size : c * tile_size + w] = tile[:h, :w]
                ok_src += 1
    mark("stitch")

    failed = ok_o == 0 or ok_n == 0
    partial = not failed and (ok_o < total_tiles or ok_n < total_tiles)
    out_dir = output_root / fid
    out_dir.mkdir(parents=True, exist_ok=True)
    failed_tiles = list(failed_tiles or [])
    tile_errors = dict(tile_errors or {})
    if failed:
        run_status = "failed"
        tile_errors.setdefault("whole_image", "切片推理存在整期缺失，未能拼接全图结果")
    elif partial:
        run_status = "partial"
        tile_errors.setdefault(
            "whole_image",
            "部分切片推理失败：缺失掩膜区域以无效值 255 标记，不计入混淆矩阵",
        )
    else:
        cv2.imwrite(str(out_dir / (fid + "_old.png")), old_pred)
        cv2.imwrite(str(out_dir / (fid + "_new.png")), new_pred)
        if ok_src:
            cv2.imwrite(str(out_dir / (fid + "_src.png")), src_img)
        old_mask_path = out_dir / (fid + "_old_mask.png")
        new_mask_path = out_dir / (fid + "_new_mask.png")
        cv2.imwrite(str(old_mask_path), old_mask)
        cv2.imwrite(str(new_mask_path), new_mask)
        write_change_matrix_csv(old_mask_path, new_mask_path, out_dir)
        run_status = "completed"

    return {
        "status": run_status,
        "message": (
            "整图推理模式：影像与 KML 图斑无交集（" + no_features_message + "），"
            "已按 512×512 切片推理并拼接全图分类结果（未联动，仅解译平台展示）"
            if not failed
            else "整图推理失败：" + no_features_message
        ),
        "total_features": 0,
        "matched_fids": 1,
        "matched_fid_list": [fid],
        "output_root": str(output_root),
        "failed_tiles": failed_tiles,
        "tile_errors": tile_errors,
        "inference_runtime": inference_runtime,
        "written_fids": 0 if failed else 1,
        "written_fid_list": [] if failed else [fid],
        "missing_fids": [],
        "stage_durations": dict(stage_durations),
        "total_seconds": round(time.monotonic() - run_started, 3),
    }


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
    allow_whole_image: bool = False,
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
        if not allow_whole_image or raw_feature_count == 0:
            return {
            "status": "no_features",
            "message": message,
            "stage_durations": dict(stage_durations),
            "total_seconds": round(time.monotonic() - run_started, 3),
        }

    if not features:
        # 整图推理模式（2026-09-18 验收反馈）：影像与 KML 图斑零交集时，
        # 按 512×512 网格切片推理并拼接全图结果，落 U<时间戳> 未联动命名空间，
        # 仅解译平台预览展示，不与 miner 矿山联动。
        return _run_whole_image_inference(
            old_tif=old_tif,
            new_tif=new_tif,
            tile_dir=tile_dir,
            mmseg_out_dir=mmseg_out_dir,
            output_root=output_root,
            model_id=model_id,
            device=device,
            no_features_message=message,
            mark=mark,
            stage_durations=stage_durations,
            run_started=run_started,
        )


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
