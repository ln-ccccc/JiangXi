from typing import Dict, List, Tuple


def run_mmseg_tiles(
    *,
    model_id: str,
    data_path: str,
    out_dir: str,
    file_names: List[str],
    device: str,
) -> Tuple[List[str], Dict[str, str], Dict]:
    from applications.interface import mmseg_inference_caller

    failed_tiles: List[str] = []
    tile_errors: Dict[str, str] = {}

    try:
        detail = mmseg_inference_caller.execute_detailed(
            model_id=model_id,
            data_path=data_path,
            out_dir=out_dir,
            names=file_names,
            device=device,
        )
    except Exception as exc:
        return list(file_names), {tile_name: str(exc) for tile_name in file_names}, {}

    results = detail.get("results", []) if isinstance(detail, dict) else []
    result_map = {str(item.get("name")): item for item in results if isinstance(item, dict)}
    for tile_name in file_names:
        expected_name = f"pred_{tile_name.rsplit('.', 1)[0]}.png"
        result = result_map.get(expected_name) or result_map.get(tile_name)
        if not result or result.get("status") != "success":
            failed_tiles.append(tile_name)
            tile_errors[tile_name] = str((result or {}).get("error") or (result or {}).get("message") or "未返回瓦片结果")

    return failed_tiles, tile_errors, detail.get("runtime", {}) if isinstance(detail, dict) else {}

