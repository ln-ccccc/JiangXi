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
    """整图推理（流式）：512×512 网格切片 → 逐行推理 → 按行写入全分辨率
    GeoTIFF + 直方图化混淆矩阵 + 降采样预览 PNG。

    内存与影像尺寸解耦：任意时刻仅驻留单行画布与降采样预览画布，
    支持 GB 级县级影像（2026-09-19 验收需求）。全分辨率产物为
    GeoTIFF（带地理参考，GIS 可直接使用），预览 PNG 供页面展示。
    """
    import cv2
    import numpy as np
    import rasterio
    from rasterio.windows import Window

    fid = "U" + str(int(time.time()))
    tile_size = 512
    preview_max = 4096
    max_pixels = 4_000_000_000  # 40 亿像素防误用上限（流式设计内存安全，运行时长随像素线性）
    tile_dir.mkdir(parents=True, exist_ok=True)
    mmseg_out_dir.mkdir(parents=True, exist_ok=True)
    mark("prep_dirs")

    with rasterio.open(old_tif) as src:
        height, width = src.height, src.width
        transform = src.transform
        crs = src.crs

    if height * width > max_pixels:
        return {
            "status": "failed",
            "message": (
                "影像尺寸 " + str(width) + "x" + str(height) + "（约 "
                + str(height * width // 1_000_000) + "00 万像素）超出整图推理上限 "
                + str(max_pixels // 1_000_000) + "00 万像素，请裁剪后重试"
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
    out_dir = output_root / fid
    out_dir.mkdir(parents=True, exist_ok=True)

    scale = min(1.0, preview_max / max(height, width))
    pv_h = max(1, round(height * scale))
    pv_w = max(1, round(width * scale))

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "uint8",
        "transform": transform,
        "crs": crs,
        "compress": "deflate",
        "nodata": 255,
    }
    profile_rgb = dict(profile, count=3, nodata=None)

    rio_old_pred = rasterio.open(out_dir / "result_old_full.tif", "w", **profile_rgb)
    rio_new_pred = rasterio.open(out_dir / "result_new_full.tif", "w", **profile_rgb)
    rio_old_mask = rasterio.open(out_dir / "mask_old_full.tif", "w", **profile)
    rio_new_mask = rasterio.open(out_dir / "mask_new_full.tif", "w", **profile)

    trans_hist = np.zeros((6, 6), dtype=np.int64)
    failed_tiles = []
    tile_errors = {}
    ok_rows = 0
    last_runtime = {}

    preview_old = np.zeros((pv_h, pv_w, 3), dtype=np.uint8)
    preview_new = np.zeros((pv_h, pv_w, 3), dtype=np.uint8)

    try:
        for r in range(n_rows):
            row_h = min(tile_size, height - r * tile_size)
            row_win = Window(0, r * tile_size, width, row_h)
            file_names = []
            for tag, tif_path in (("o", old_tif), ("n", new_tif)):
                with rasterio.open(tif_path) as s2:
                    for c in range(n_cols):
                        win = Window(c * tile_size, r * tile_size, tile_size, tile_size)
                        data = s2.read(window=win, boundless=True, fill_value=0)
                        arr = np.moveaxis(data, 0, -1)
                        if arr.shape[2] > 3:
                            arr = arr[:, :, :3]
                        elif arr.shape[2] == 1:
                            arr = np.repeat(arr, 3, axis=2)
                        png = tile_dir / (fid + "_tile_" + tag + str(r) + "_" + str(c) + ".png")
                        cv2.imwrite(str(png), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
                        file_names.append(png.name)
            mark("tiles_r" + str(r))

            failed_row, tile_errors_row, inference_runtime = run_mmseg_tiles(
                model_id=model_id,
                data_path=str(tile_dir),
                out_dir=str(mmseg_out_dir),
                file_names=file_names,
                device=device,
            )
            if inference_runtime:
                last_runtime = inference_runtime
            failed_tiles.extend(failed_row or [])
            tile_errors.update(tile_errors_row or {})
            mark("inference_r" + str(r))

            row_old = np.full((row_h, width, 3), 255, dtype=np.uint8)
            row_new = np.full((row_h, width, 3), 255, dtype=np.uint8)
            row_mask_old = np.full((row_h, width), 255, dtype=np.uint8)
            row_mask_new = np.full((row_h, width), 255, dtype=np.uint8)
            row_ok = 0
            for c in range(n_cols):
                base_name = fid + "_tile_o" + str(r) + "_" + str(c)
                n_name = fid + "_tile_n" + str(r) + "_" + str(c)
                x0 = c * tile_size
                pred_o = cv2.imread(str(mmseg_out_dir / ("pred_" + base_name + ".png")), cv2.IMREAD_COLOR)
                pred_n = cv2.imread(str(mmseg_out_dir / ("pred_" + n_name + ".png")), cv2.IMREAD_COLOR)
                mask_o = cv2.imread(str(mmseg_out_dir / ("mask_" + base_name + ".png")), cv2.IMREAD_UNCHANGED)
                mask_n = cv2.imread(str(mmseg_out_dir / ("mask_" + n_name + ".png")), cv2.IMREAD_UNCHANGED)
                if pred_o is None or pred_n is None or mask_o is None or mask_n is None:
                    failed_tiles.append(base_name)
                    continue
                if pred_o.ndim == 3:
                    pred_o = pred_o[:, :, ::-1]
                if pred_n.ndim == 3:
                    pred_n = pred_n[:, :, ::-1]
                if mask_o.ndim == 3:
                    mask_o = mask_o[:, :, 0]
                if mask_n.ndim == 3:
                    mask_n = mask_n[:, :, 0]
                w_valid = min(tile_size, width - x0)
                row_old[:, x0 : x0 + w_valid] = pred_o[:row_h, :w_valid]
                row_new[:, x0 : x0 + w_valid] = pred_n[:row_h, :w_valid]
                row_mask_old[:, x0 : x0 + w_valid] = mask_o[:row_h, :w_valid]
                row_mask_new[:, x0 : x0 + w_valid] = mask_n[:row_h, :w_valid]
                row_ok += 1

            if row_ok:
                ok_rows += 1
                win = Window(0, r * tile_size, width, row_h)
                rio_old_pred.write(np.moveaxis(row_old, -1, 0), window=win)
                rio_new_pred.write(np.moveaxis(row_new, -1, 0), window=win)
                rio_old_mask.write(row_mask_old, indexes=1, window=win)
                rio_new_mask.write(row_mask_new, indexes=1, window=win)

                valid = (row_mask_old < 6) & (row_mask_new < 6)
                ov = row_mask_old[valid].astype(np.int64)
                nv = row_mask_new[valid].astype(np.int64)
                np.add.at(trans_hist, (ov, nv), 1)

                strip_h = max(1, round(row_h * scale))
                strip_o = cv2.resize(row_old, (pv_w, strip_h), interpolation=cv2.INTER_AREA)
                strip_n = cv2.resize(row_new, (pv_w, strip_h), interpolation=cv2.INTER_AREA)
                y0 = round(r * tile_size * scale)
                y1 = min(pv_h, y0 + strip_h)
                if y1 > y0:
                    preview_old[y0:y1] = strip_o[: y1 - y0]
                    preview_new[y0:y1] = strip_n[: y1 - y0]
            mark("row_r" + str(r))
    finally:
        rio_old_pred.close()
        rio_new_pred.close()
        rio_old_mask.close()
        rio_new_mask.close()

    # 预览 _src：o 期原始影像降采样（与结果同网格）
    preview_src = np.zeros((pv_h, pv_w, 3), dtype=np.uint8)
    with rasterio.open(old_tif) as s3:
        for y0 in range(0, pv_h, 256):
            y1 = min(pv_h, y0 + 256)
            row_win = Window(0, min(height - 1, round(y0 / scale)), width, max(1, round((y1 - y0) / scale)))
            data = s3.read(window=row_win, boundless=True, fill_value=0)
            arr = np.moveaxis(data, 0, -1)
            if arr.shape[2] > 3:
                arr = arr[:, :, :3]
            strip = cv2.resize(arr, (pv_w, y1 - y0), interpolation=cv2.INTER_AREA)
            preview_src[y0:y1] = strip[: y1 - y0]
    cv2.imwrite(str(out_dir / (fid + "_src.png")), cv2.cvtColor(preview_src, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out_dir / (fid + "_old.png")), cv2.cvtColor(preview_old, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out_dir / (fid + "_new.png")), cv2.cvtColor(preview_new, cv2.COLOR_RGB2BGR))
    mark("preview")

    class_names = ["grassland", "forest", "building", "road", "bareground", "water"]
    lines = ["class," + ",".join(class_names)]
    for i, name in enumerate(class_names):
        lines.append(name + "," + ",".join(str(int(v)) for v in trans_hist[i]))
    (out_dir / "change_matrix_pixels.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    row_sum = trans_hist.sum(axis=1, keepdims=True)
    pct = np.divide(
        trans_hist, row_sum, out=np.zeros_like(trans_hist, dtype=float), where=row_sum > 0
    ) * 100.0
    lines = ["class," + ",".join(class_names)]
    for i, name in enumerate(class_names):
        lines.append(name + "," + ",".join("{:.2f}".format(v) for v in pct[i]))
    (out_dir / "change_matrix_percent_rownorm.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    all_failed = ok_rows == 0
    partial = (not all_failed) and (len(failed_tiles) > 0 or ok_rows < n_rows)
    if all_failed:
        run_status = "failed"
        tile_errors.setdefault("whole_image", "全部切片推理失败，未能生成结果")
    elif partial:
        run_status = "partial"
        tile_errors.setdefault(
            "whole_image",
            "部分切片推理失败（" + str(len(failed_tiles)) + " 片），失败区域在结果中以空白标示",
        )
    else:
        run_status = "completed"

    return {
        "status": run_status,
        "message": (
            (
                "整图推理模式：影像与 KML 图斑无交集（" + no_features_message + "），"
                "已按 512×512 切片推理并流式拼接全图结果（未联动，仅解译平台展示；"
                "全分辨率 GeoTIFF 已随结果输出）"
            )
            if not all_failed
            else "整图推理失败：" + no_features_message
        ),
        "total_features": 0,
        "matched_fids": 1,
        "matched_fid_list": [fid],
        "output_root": str(output_root),
        "failed_tiles": failed_tiles,
        "tile_errors": tile_errors,
        "inference_runtime": last_runtime,
        "written_fids": 0 if all_failed else 1,
        "written_fid_list": [] if all_failed else [fid],
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
