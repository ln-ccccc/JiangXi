import json
import os
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from sqlalchemy import desc

from applications.auth.guard import ensure_logged_in
from applications.common.curd import model_to_dicts
from applications.common.path_global import generate_dir, generate_url, fun_type_2, fun_type_3, fun_type_4, fun_type_5, up_dir
from applications.common.utils import type_utils
from applications.common.utils.http import fail_api, success_api, table_api
from applications.common.utils.type_utils import items_handle
from applications.common.utils.upload import img_url_handle
from applications.common.utils.safe_paths import PathValidationError, resolve_managed_file, resolve_output_file
from applications.interface.analysis import handle, spectral_index_calculation, terrain_classification
from applications.interface.inference_device import resolve_inference_device
from applications.kml_roi.service import run_kml_roi_inference
from applications.models.analysis import Analysis
from applications.schemas import AnalysisSchema
from applications.project_hub.tbbh_identity import normalize_tbbh

analysis_api = Blueprint('analysis_api', __name__, url_prefix='/api/analysis')
repo_root = Path(__file__).resolve().parents[3]
miner_change_output_root = Path(
    os.getenv("MINER_CHANGE_OUTPUT_ROOT") or repo_root / "miner" / "change_matrix_outputs"
).expanduser().resolve()
upload_path_prefix = "static/upload/"


def _asset_manifest_path():
    return Path(
        os.getenv("JIANGXI_ASSET_MANIFEST_PATH")
        or repo_root / "docker" / "standalone" / "runtime_data" / "Jiangxi_asset_manifest.json"
    ).expanduser().resolve()


def _map_fid_to_tbbh(map_fid):
    try:
        map_fid = int(map_fid)
    except (TypeError, ValueError):
        return None
    manifest_path = _asset_manifest_path()
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for raw_tbbh, raw_map_fid in (manifest.get("mapping", {}).get("tbbh_to_map_fid") or {}).items():
            if int(raw_map_fid) == map_fid:
                return normalize_tbbh(raw_tbbh)
    except (OSError, TypeError, ValueError):
        return None
    return None


def _tbbh_to_map_fid(tbbh):
    try:
        normalized_tbbh = normalize_tbbh(tbbh)
    except ValueError:
        return None
    manifest_path = _asset_manifest_path()
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for raw_tbbh, raw_map_fid in (manifest.get("mapping", {}).get("tbbh_to_map_fid") or {}).items():
            if normalize_tbbh(raw_tbbh) == normalized_tbbh:
                return int(raw_map_fid)
    except (OSError, TypeError, ValueError):
        return None
    return None


def _history_identity(map_fid_dir):
    manifest_path = map_fid_dir / "result_manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        result = json.loads(manifest_path.read_text(encoding="utf-8"))
        map_fid = int(result.get("map_fid"))
        if str(map_fid) != map_fid_dir.name:
            return None
        tbbh = normalize_tbbh(result.get("tbbh"))
    except (OSError, TypeError, ValueError):
        return None
    if _map_fid_to_tbbh(map_fid) != tbbh:
        return None
    return {"tbbh": tbbh, "map_fid": map_fid}


def _normalize_uploaded_tiff_name(value):
    text = str(value or "").strip().replace("\\", "/")
    if text.startswith(upload_path_prefix):
        return text[len(upload_path_prefix):]
    return text


@analysis_api.before_request
def require_analysis_auth():
    return ensure_logged_in()


def _iter_flash_records():
    records = []
    if not miner_change_output_root.exists():
        return records

    for fid_dir in miner_change_output_root.iterdir():
        if not fid_dir.is_dir() or fid_dir.is_symlink():
            continue
        identity = _history_identity(fid_dir)
        if identity is None:
            continue
        map_fid = identity["map_fid"]
        tbbh = identity["tbbh"]
        for p in fid_dir.glob("*.png"):
            if p.is_symlink():
                continue
            name = p.name
            if "_mask" in name:
                continue
            if "+" not in name:
                continue
            # keep year-naming outputs, e.g. 11192+2024.png
            stem = p.stem
            parts = stem.split("+", 1)
            if len(parts) != 2 or not parts[1].isdigit():
                continue
            try:
                target = resolve_output_file(miner_change_output_root, str(map_fid), name, {".png"})
            except PathValidationError:
                continue
            if not target.is_file():
                continue
            records.append({
                "record_id": f"{tbbh}|{name}",
                "tbbh": tbbh,
                "map_fid": map_fid,
                "filename": name,
                "mtime": target.stat().st_mtime,
            })
    records.sort(key=lambda x: x["mtime"], reverse=True)
    return records


@analysis_api.get('/show/<analysis_type>')
def show_result(analysis_type):
    if not hasattr(type_utils, analysis_type):
        return fail_api("当前类型暂未开放")

    page = int(request.args.get('page', 1) or 1)
    limit = int(request.args.get('limit', 10) or 10)
    query = Analysis.query.filter_by(type=getattr(type_utils, analysis_type)).order_by(desc(Analysis.create_time))

    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    data = model_to_dicts(schema=AnalysisSchema, data=pagination.items)
    data = items_handle(data)

    return table_api(data=data, count=pagination.total)


@analysis_api.post('/semantic_segmentation')
def semantic_segmentation_api():
    req_json = request.json or {}
    model_path = req_json.get("model_path") or "mmseg:cc-ln/CUGRS"
    if not str(model_path).startswith("mmseg:"):
        return fail_api("地物分类仅支持多要素模型 mmseg:cc-ln/CUGRS")

    img_list = req_json.get("list")
    if not img_list:
        return fail_api("请上传图片")

    step1_ = req_json.get("prehandle")
    step2_ = req_json.get("denoise")
    if step1_ not in (0, fun_type_2, fun_type_4) or step2_ not in (0, fun_type_3, fun_type_5):
        return fail_api("参数异常")

    try:
        terrain_classification(
            model_path,
            up_dir,
            generate_dir,
            img_list,
            step1_,
            step2_,
            type_=3,
            device=resolve_inference_device()["effective_device"],
        )
        return success_api()
    except Exception as e:
        return fail_api(f"推理失败: {str(e)}")

@analysis_api.post('/image_pre')
def image_pre_api():
    req_json = request.json or {}
    img_list = req_json.get("list")
    step1_ = req_json.get("prehandle")
    type_ = req_json.get("type")

    if not img_list:
        return fail_api("请上传图片")
    if step1_ not in (fun_type_2, fun_type_4):
        return fail_api("请求参数异常")
    if type_ == 1:
        return fail_api("当前模式不支持")

    temps = [img_url_handle(u) for u in img_list]
    imgs = handle(step1_, temps, up_dir, generate_dir)
    for i, img in enumerate(imgs):
        imgs[i] = generate_url + img
    return success_api(data=imgs)


@analysis_api.post('/spectral_indices')
def spectral_indices_api():
    req_json = request.json or {}
    img_list = req_json.get("list")
    if not img_list:
        return fail_api("请上传图片")

    index_type = req_json.get("index_type", "NDVI")
    year = req_json.get("year", "")
    band_map = req_json.get("band_map", {})
    kml_path = req_json.get("kml_path")
    try:
        tbbh = normalize_tbbh(req_json.get("tbbh"))
    except ValueError as exc:
        return fail_api(str(exc)), 400
    map_fid = _tbbh_to_map_fid(tbbh)
    if map_fid is None:
        return fail_api(f"TBBH 不存在: {tbbh}"), 404
    # 计算核心使用小写键（nir/red/green/swir），这里统一标准化避免前端大小写差异导致映射失效
    normalized_band_map = {str(k).lower(): v for k, v in (band_map or {}).items()}

    try:
        result = spectral_index_calculation(
            up_dir,
            generate_dir,
            img_list,
            index_type,
            year,
            normalized_band_map,
            type_=8,
            kml_path=kml_path,
            fid=map_fid,
            tbbh=tbbh,
        )
        for record in result.get("records", []) if isinstance(result, dict) else []:
            record["tbbh"] = tbbh
            record["map_fid"] = map_fid
            record.pop("matched_fid_list", None)
            record.pop("fid_stats", None)
        if isinstance(result, dict):
            result["tbbh"] = tbbh
            result["map_fid"] = map_fid
            result["matched_tbbh_list"] = [tbbh]
            result.pop("matched_fid_list", None)
        warnings = result.get("sync_warnings", []) if isinstance(result, dict) else []
        blocking_warnings = [
            item for item in warnings
            if item.get("reason") not in ("missing_year", "no_fid_stats")
        ]
        if blocking_warnings:
            return success_api(msg="计算完成，同步部分失败", data=result)
        if warnings:
            return success_api(msg="计算完成，未同步部分Miner指数", data=result)
        return success_api(data=result)
    except Exception as e:
        return fail_api(f"计算失败: {str(e)}")


@analysis_api.post('/kml_roi_inference')
def kml_roi_inference_api():
    req_json = request.json or {}
    try:
        if req_json.get("output_root"):
            raise PathValidationError("不支持自定义输出目录")
        input_root = current_app.config["KML_ROI_INPUT_ROOT"]
        kml_root = current_app.config["KML_ROI_KML_ROOT"]
        default_kmz_name = Path(current_app.config["MINER_DEFAULT_KMZ_PATH"]).name
        old_tif_name = _normalize_uploaded_tiff_name(req_json.get("old_tif_path"))
        new_tif_name = _normalize_uploaded_tiff_name(
            req_json.get("new_tif_path") or old_tif_name
        )
        old_tif_path = resolve_managed_file(input_root, old_tif_name, {".tif", ".tiff"})
        new_tif_path = resolve_managed_file(
            input_root,
            new_tif_name,
            {".tif", ".tiff"},
        )
        kml_path = resolve_managed_file(
            kml_root,
            req_json.get("kml_path") or default_kmz_name,
            {".kml", ".kmz"},
        )
        if not old_tif_path.is_file() or not new_tif_path.is_file() or not kml_path.is_file():
            raise PathValidationError("推理输入文件不存在")
        data = run_kml_roi_inference(
            old_tif_path=str(old_tif_path),
            new_tif_path=str(new_tif_path),
            kml_path=str(kml_path),
            output_root=str(miner_change_output_root),
            device=resolve_inference_device()["effective_device"],
            limit=int(req_json.get('limit', 0) or 0),
            year=req_json.get('year') or '',
            old_year=req_json.get('old_year') or '',
            new_year=req_json.get('new_year') or '',
            manifest_path=str(_asset_manifest_path()),
        )
        if data.get("status") == "failed":
            errors = data.get("tile_errors") or {}
            detail = next(iter(errors.values()), "地物分类未生成任何结果")
            return jsonify(
                success=False,
                code=1,
                msg=str(detail),
                data=data,
            ), 500
        if data.get("status") == "partial":
            return success_api(msg="地物分类部分成功", data=data)
        return success_api(data=data)
    except PathValidationError as exc:
        return fail_api(str(exc)), 400
    except Exception as e:
        return fail_api(str(e))


@analysis_api.get('/kml_roi_output/<tbbh>/<filename>')
def kml_roi_output_file(tbbh, filename):
    try:
        normalized_tbbh = normalize_tbbh(tbbh)
    except ValueError as exc:
        return fail_api(str(exc)), 400
    map_fid = _tbbh_to_map_fid(normalized_tbbh)
    if map_fid is None:
        return fail_api(f"TBBH 不存在: {normalized_tbbh}"), 404
    try:
        target = resolve_output_file(miner_change_output_root, str(map_fid), filename, {".png"})
    except PathValidationError as exc:
        return fail_api(str(exc)), 400
    if not target.is_file():
        return fail_api("结果目录不存在")
    return send_from_directory(str(target.parent), target.name)


@analysis_api.get('/kml_roi_history')
def kml_roi_history_list():
    page = int(request.args.get('page', 1) or 1)
    limit = int(request.args.get('limit', 20) or 20)
    page = max(1, page)
    limit = max(1, min(100, limit))

    records = _iter_flash_records()
    total = len(records)
    start = (page - 1) * limit
    end = start + limit
    page_items = records[start:end]

    data = []
    for idx, rec in enumerate(page_items):
        tbbh = rec["tbbh"]
        map_fid = rec["map_fid"]
        filename = rec["filename"]
        img_url = f"/api/analysis/kml_roi_output/{tbbh}/{filename}"
        stem = Path(filename).stem
        src_name = f"{stem}_src.png"
        src_path = miner_change_output_root / str(map_fid) / src_name
        before_url = f"/api/analysis/kml_roi_output/{tbbh}/{src_name}" if src_path.exists() else img_url
        data.append({
            "id": total - start - idx,
            "record_id": rec["record_id"],
            "type": "地物分类",
            "before_img": before_url,
            "after_img": img_url,
            "data": {"mode": "flash", "tbbh": tbbh, "map_fid": map_fid, "file": filename},
        })
    return table_api(data=data, count=total, limit=limit)


@analysis_api.delete('/kml_roi_history/item')
def kml_roi_history_remove_one():
    req_json = request.json or {}
    record_id = str(req_json.get("record_id", "")).strip()
    if "|" not in record_id:
        return fail_api("参数异常")
    tbbh, filename = record_id.split("|", 1)
    if tbbh in {".", ".."} or "/" in tbbh or "\\" in tbbh:
        return fail_api("TBBH 参数不合法"), 400
    try:
        normalized_tbbh = normalize_tbbh(tbbh)
    except ValueError as exc:
        return fail_api(str(exc)), 400
    map_fid = _tbbh_to_map_fid(normalized_tbbh)
    if map_fid is None:
        return fail_api(f"TBBH 不存在: {normalized_tbbh}"), 404
    try:
        target = resolve_output_file(miner_change_output_root, str(map_fid), filename, {".png"})
    except PathValidationError as exc:
        return fail_api(str(exc)), 400
    if not target.is_file():
        return fail_api("记录不存在")
    target.unlink()
    src_target = target.with_name(f"{target.stem}_src.png")
    if src_target.exists():
        src_target.unlink()
    return success_api(msg="删除成功")


@analysis_api.delete('/kml_roi_history/clear')
def kml_roi_history_clear():
    removed = 0
    for rec in _iter_flash_records():
        map_fid = rec["map_fid"]
        filename = rec["filename"]
        try:
            target = resolve_output_file(miner_change_output_root, str(map_fid), filename, {".png"})
            src_target = resolve_output_file(
                miner_change_output_root, str(map_fid), f"{Path(filename).stem}_src.png", {".png"}
            )
        except PathValidationError:
            continue
        if target.is_file():
            target.unlink()
            removed += 1
        if src_target.is_file():
            src_target.unlink()
    return success_api(msg="清理成功", data={"removed": removed})
