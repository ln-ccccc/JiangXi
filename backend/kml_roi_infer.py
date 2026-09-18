#!/usr/bin/env python3
"""KML ROI inference pipeline for large GeoTIFFs."""

import argparse
import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path

from applications.region_source import resolve_default_jiangxi_kmz
from applications.kml_roi.pipeline import run_kml_roi_pipeline
from applications.interface.inference_device import resolve_inference_device

BUSY_EXIT_CODE = 3
BUSY_MESSAGE = "已有一个图斑推理任务正在执行，请等待完成后再提交"


def _request_shutdown(signum, _frame):
    # SIGTERM 默认直接终止不走 finally，孙进程（mmseg_segmentation.py）会孤儿化
    # 继续占用 GPU；转成 SystemExit 让调用方的 finally 清理链生效
    raise SystemExit(128 + signum)


def _acquire_run_lock(output_root: Path, lock_fd: int = -1):
    """跨进程推理互斥锁。

    Flask subprocess 与 miner BFF execFile 两条链最终都运行本脚本，
    在此统一串行化，防止并发推理交叉写共享 output_root/<fid>/。
    fcntl 不可用（Windows 开发机）时跳过互斥。
    lock_fd >= 0 时父进程（Flask 合并链路）已持锁并把 fd 传入——直接复用，
    不再 flock（重复取会 busy 退出，自己堵自己）；锁由父进程统一释放。
    """
    if lock_fd is not None and lock_fd >= 0:
        return os.fdopen(lock_fd, "w")
    try:
        import fcntl
    except ImportError:
        print("[kml-roi-infer] fcntl 不可用，跳过跨进程推理锁（仅限开发环境）", file=sys.stderr)
        return None
    lock_path = output_root / ".kml_roi_infer.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "w")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        print(json.dumps({"status": "busy", "error": BUSY_MESSAGE}, ensure_ascii=False))
        raise SystemExit(BUSY_EXIT_CODE)
    return handle


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
    parser.add_argument(
        "--lock_fd",
        type=int,
        default=-1,
        help="父进程已持有的推理锁 fd（Flask 合并链路传入时直接复用，不再 flock）",
    )
    parser.add_argument("--year", default="", help="Single snapshot year (YYYY). Stores outputs as {FID}+{YYYY}.")
    parser.add_argument("--old_year", default="", help="Old year label (YYYY) for old_tif")
    parser.add_argument("--new_year", default="", help="New year label (YYYY) for new_tif")
    parser.add_argument(
        "--manifest",
        default=os.environ.get("JIANGXI_ASSET_MANIFEST_PATH", ""),
        help="江西 TBBH/map_fid manifest path",
    )
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, _request_shutdown)
    old_tif = Path(args.old_tif).expanduser().resolve()
    new_tif = Path(args.new_tif).expanduser().resolve()
    kml_path = Path(args.kml).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve()
    # 进程存活期间持锁；GPU 串行语义 + 防并发交叉写共享产物目录。
    # --lock_fd >= 0（Flask 合并链路）时父进程已持锁，这里只复用不重复获取。
    run_lock = _acquire_run_lock(output_root, lock_fd=args.lock_fd)
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
        linked_fids={str(k) for k in map_fid_to_tbbh},
    )
    matched_fids = summary.get("matched_fid_list") or []
    # 非联动模式（2026-09-18 验收反馈）：清单外 fid 已被管线改写为 U<fid>，
    # 正常出结果但不映射 TBBH、不写联动 result_manifest，miner 天然不可见。
    linked_matched = [fid for fid in matched_fids if not str(fid).startswith("U")]
    unlinked_matched = [fid for fid in matched_fids if str(fid).startswith("U")]
    summary["unlinked_count"] = len(unlinked_matched)
    if unlinked_matched:
        summary["message"] = (
            "KML 含 " + str(len(unlinked_matched)) + " 个清单外图斑，已按未联动模式推理："
            "结果仅在解译平台展示，不与 miner 矿山（TBBH）关联"
        )
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
    written_results = []
    for raw_fid in written_fids:
        if str(raw_fid).startswith("U"):
            fid_dir = output_root / str(raw_fid)
            files = sorted(
                f.name
                for f in fid_dir.glob("*.png")
                if not f.name.endswith("_mask.png") and not f.name.endswith("_src.png")
            ) if fid_dir.exists() else []
            written_results.append(
                {
                    "unlinked": True,
                    "fid": str(raw_fid),
                    "source_output_dir": str(raw_fid),
                    "files": files,
                }
            )
            continue
        written_results.append(
            {
                "tbbh": map_fid_to_tbbh[int(raw_fid)],
                "map_fid": int(raw_fid),
                "source_output_dir": str(int(raw_fid)),
            }
        )
    summary["matched_tbbh_list"] = [map_fid_to_tbbh[int(fid)] for fid in linked_matched]
    summary["written_tbbh_list"] = [
        map_fid_to_tbbh[int(fid)] for fid in written_fids if not str(fid).startswith("U")
    ]
    summary["written_results"] = written_results
    summary["result_manifests"] = result_manifests
    summary.pop("matched_fid_list", None)
    summary.pop("written_fid_list", None)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

