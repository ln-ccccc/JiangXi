import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import cv2
import numpy as np
from applications.kml_roi.change_matrix import write_change_matrix_csv, write_class_ratio_json
from applications.common.utils.safe_paths import resolve_output_directory
from applications.kml_roi.raster_ops import (
    border_connected_bg_mask,
    crop_bbox_from_raster,
    crop_prediction_by_polygon,
    draw_polygon_boundary_on_prediction,
    tif_to_png,
)


def parse_year(v: Optional[str]) -> Optional[int]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    if not s.isdigit():
        return None
    if len(s) != 4:
        return None
    y = int(s)
    if y < 1800 or y > 2200:
        return None
    return y


def name_base(fid: str, tag: str, use_year_naming: bool, variant_suffix: str = "") -> str:
    tag_s = str(tag).strip()
    if use_year_naming:
        return f"{fid}+{tag_s}{variant_suffix}"
    return f"{fid}_{tag_s}{variant_suffix}"


def prepare_tiles(
    old_tif: Path,
    new_tif: Path,
    features: List[Tuple[str, Dict]],
    tile_dir: Path,
    *,
    year: Optional[str] = None,
    old_year: Optional[str] = None,
    new_year: Optional[str] = None,
) -> Tuple[List[str], List[str], Dict[str, List[Dict]]]:
    tile_dir.mkdir(parents=True, exist_ok=True)
    matched_fids: List[str] = []
    file_names: List[str] = []
    variants_by_fid: Dict[str, List[Dict]] = {}

    y_single = parse_year(year)
    y_old = parse_year(old_year)
    y_new = parse_year(new_year)

    if y_single is not None:
        variants = [("single", str(y_single), old_tif)]
        use_year_naming = True
    elif y_old is not None and y_new is not None:
        variants = [("old", str(y_old), old_tif), ("new", str(y_new), new_tif)]
        use_year_naming = True
    else:
        variants = [("old", "old", old_tif), ("new", "new", new_tif)]
        use_year_naming = False

    # 同 fid 的多个 Placemark（同场地多图斑）按出现顺序编为 variant：
    # 第 1 组沿用历史命名保证 348 主链路（fid 唯一）行为不变；
    # 第 2 组起加 _v2/_v3 后缀，避免瓦片与推理产物同名互相覆盖。
    variant_group_counts: Dict[str, int] = {}

    for fid, geom in features:
        occurrence = variant_group_counts.get(fid, 0) + 1
        variant_suffix = "" if occurrence == 1 else f"_v{occurrence}"
        variant_specs: List[Dict] = []
        for _, tag, tif_path in variants:
            dst_base = name_base(fid, tag, use_year_naming, variant_suffix)
            src_base = f"{dst_base}_tile"
            cropped_tif = tile_dir / f"{src_base}.tif"
            cropped_png = tile_dir / f"{src_base}.png"

            ok_crop = crop_bbox_from_raster(tif_path, geom, cropped_tif)
            if not ok_crop:
                continue
            ok_png = tif_to_png(cropped_tif, cropped_png)
            if not ok_png:
                continue

            file_names.append(f"{src_base}.png")
            variant_specs.append(
                {
                    "dst_base": dst_base,
                    "src_base": src_base,
                    "raster_path": tif_path,
                    "geom": geom,
                    "already_cropped": True,
                }
            )

        if variant_specs:
            variant_group_counts[fid] = occurrence
            if fid not in variants_by_fid:
                matched_fids.append(fid)
            variants_by_fid.setdefault(fid, []).extend(variant_specs)

    return matched_fids, file_names, variants_by_fid


def scan_year_masks(fid: str, fid_dir: Path) -> List[Tuple[int, Path, Path]]:
    out: List[Tuple[int, Path, Path]] = []
    prefix = f"{fid}+"
    for p in fid_dir.glob(f"{prefix}*_mask.png"):
        name = p.name
        if not name.startswith(prefix):
            continue
        year_part = name[len(prefix) :].split("_mask.png")[0]
        y = parse_year(year_part)
        if y is None:
            continue
        img_path = fid_dir / f"{fid}+{y}.png"
        out.append((y, img_path, p))
    out.sort(key=lambda t: t[0])
    return out


# 同 fid 第二图斑（F1 修复）产物的变体 stem：`{fid}+{YYYY}_vN` / `{fid}_{YYYY}_vN`
# （年命名）与 `{fid}_{old|new}_vN`（无年命名）。parse_year 对 "2024_v2" 返回 None，
# 这些文件不会进 scan_year_masks，统计链语义因此保持不变——但 cleanup 不得因此
# 把它们当垃圾误删。
_VARIANT_STEM_PATTERNS = (
    re.compile(r"^\+(\d{4})_v\d+$"),
    re.compile(r"^_(\d{4})_v\d+$"),
    re.compile(r"^_(?:old|new)_v\d+$"),
)


def _variant_keep_names(fid: str, fid_dir: Path, kept_years: Optional[Set[int]]) -> Set[str]:
    """清理白名单的 `_vN` 变体补充集。

    kept_years 传 None 时全部保留（无年命名产物或无法判定年份的保守场景）；
    传入保留年份集合时，年命名变体仅当年份仍在保留期内才保护，随基础年份
    一起淘汰。
    """
    keep: Set[str] = set()
    for p in fid_dir.glob(f"{fid}*_mask.png"):
        name = p.name
        if not name.endswith("_mask.png"):
            continue
        stem = name[: -len("_mask.png")]
        if not stem.startswith(fid):
            continue
        tail = stem[len(fid) :]
        matched = False
        for pattern in _VARIANT_STEM_PATTERNS:
            m = pattern.match(tail)
            if not m:
                continue
            if kept_years is not None and m.lastindex and m.group(1) and m.group(1).isdigit():
                if int(m.group(1)) not in kept_years:
                    break
            matched = True
            break
        if not matched:
            continue
        keep.add(name)
        keep.add(f"{stem}.png")
        keep.add(f"{stem}_src.png")
    return keep


def cleanup_output_dir(fid: str, fid_dir: Path, keep_last_years: int = 3) -> int:
    removed = 0
    year_masks = scan_year_masks(fid, fid_dir)
    keep = set()
    if year_masks:
        if keep_last_years and keep_last_years > 0 and len(year_masks) > keep_last_years:
            year_masks = year_masks[-keep_last_years:]
        for _, img_path, mask_path in year_masks:
            keep.add(img_path.name)
            keep.add(Path(mask_path).name)
            keep.add(f"{img_path.stem}_src.png")
        keep.update(
            {
                "change_matrix_pixels.csv",
                "change_matrix_percent_rownorm.csv",
                "class_ratio_percent.json",
            }
        )
        # F1 同 fid 多图斑的 _vN 变体随其年份进保留集（parse_year("2024_v2")
        # 返回 None 不进 scan_year_masks，统计链语义不变，但清理不得误删）
        kept_years = {y for y, _, _ in year_masks}
        keep |= _variant_keep_names(fid, fid_dir, kept_years)
    else:
        keep.update(
            {
                f"{fid}_old.png",
                f"{fid}_new.png",
                f"{fid}_old_mask.png",
                f"{fid}_new_mask.png",
                "change_matrix_pixels.csv",
                "change_matrix_percent_rownorm.csv",
                "class_ratio_percent.json",
            }
        )
        # 无年命名产物的保守场景：_vN 变体全部保留
        keep |= _variant_keep_names(fid, fid_dir, None)

    for p in fid_dir.iterdir():
        if not p.is_file():
            continue
        if p.name in keep:
            continue
        p.unlink()
        removed += 1
    return removed


def _write_masked_prediction_from_tile(
    *,
    pred_image_path: Path,
    pred_mask_path: Path,
    tile_image_path: Path,
    out_image_path: Path,
    out_mask_path: Path,
) -> bool:
    pred_img = cv2.imread(str(pred_image_path), cv2.IMREAD_COLOR)
    pred_mask = cv2.imread(str(pred_mask_path), cv2.IMREAD_UNCHANGED)
    tile_img = cv2.imread(str(tile_image_path), cv2.IMREAD_COLOR)
    if pred_img is None or pred_mask is None or tile_img is None:
        return False
    if pred_mask.ndim == 3:
        pred_mask = pred_mask[:, :, 0]
    if tile_img.shape[:2] != pred_img.shape[:2]:
        tile_img = cv2.resize(tile_img, (pred_img.shape[1], pred_img.shape[0]), interpolation=cv2.INTER_NEAREST)

    valid = ~border_connected_bg_mask(tile_img)
    out_img = np.zeros_like(pred_img)
    out_img[valid] = pred_img[valid]
    out_mask = np.full(pred_mask.shape, 255, dtype=np.uint8)
    out_mask[valid] = pred_mask[valid]

    ok_img = bool(cv2.imwrite(str(out_image_path), out_img))
    ok_mask = bool(cv2.imwrite(str(out_mask_path), out_mask))
    return ok_img and ok_mask


def distribute_outputs(
    fids: List[str],
    mmseg_dir: Path,
    output_root: Path,
    variants_by_fid: Dict[str, List[Dict]],
    tile_dir: Optional[Path] = None,
) -> Dict:
    written = 0
    written_fid_list: List[str] = []
    missing: List[str] = []

    for fid in fids:
        fid_dir = resolve_output_directory(output_root, fid)
        variant_specs = variants_by_fid.get(fid) or []
        if not variant_specs:
            missing.append(fid)
            continue

        fid_dir.mkdir(parents=True, exist_ok=True)

        copied_any = False
        for spec in variant_specs:
            src_base = spec["src_base"]
            dst_base = spec["dst_base"]
            src_img = mmseg_dir / f"pred_{src_base}.png"
            src_mask = mmseg_dir / f"mask_{src_base}.png"
            dst_img = fid_dir / f"{dst_base}.png"
            dst_mask = fid_dir / f"{dst_base}_mask.png"
            dst_src = fid_dir / f"{dst_base}_src.png"

            if not src_img.exists() or not src_mask.exists():
                continue
            if spec.get("already_cropped"):
                tile_img = tile_dir / f"{src_base}.png" if tile_dir is not None else None
                if tile_img is not None and tile_img.exists():
                    ok_crop = draw_polygon_boundary_on_prediction(
                        pred_image_path=src_img,
                        pred_mask_path=src_mask,
                        tile_image_path=tile_img,
                        raster_path=tile_dir / f"{src_base}.tif",
                        geom_4326=spec.get("geom"),
                        out_image_path=dst_img,
                        out_mask_path=dst_mask,
                    )
                    if ok_crop:
                        shutil.copy2(tile_img, dst_src)
                else:
                    shutil.copy2(src_img, dst_img)
                    shutil.copy2(src_mask, dst_mask)
                    ok_crop = True
            else:
                ok_crop = crop_prediction_by_polygon(
                    pred_image_path=src_img,
                    pred_mask_path=src_mask,
                    raster_path=Path(spec["raster_path"]),
                    geom_4326=spec["geom"],
                    out_image_path=dst_img,
                    out_mask_path=dst_mask,
                )
            copied_any = copied_any or ok_crop

        if not copied_any:
            missing.append(fid)
            continue

        year_masks = scan_year_masks(fid, fid_dir)
        if len(year_masks) >= 2:
            old_y, _, old_mask = year_masks[-2]
            new_y, _, new_mask = year_masks[-1]
            if old_y != new_y:
                write_change_matrix_csv(old_mask, new_mask, fid_dir)

        if year_masks:
            write_class_ratio_json(fid=fid, year_masks=year_masks, out_dir=fid_dir)

        written += 1
        written_fid_list.append(fid)

    return {
        "written_fids": written,
        "written_fid_list": written_fid_list,
        "missing_fids": missing,
    }
