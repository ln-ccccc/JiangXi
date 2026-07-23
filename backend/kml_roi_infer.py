#!/usr/bin/env python3
"""KML ROI inference pipeline for large GeoTIFFs."""

import argparse
import json
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
        default=str(repo_root / "miner" / "change_matrix_outputs"),
        help="Output root path",
    )
    parser.add_argument(
        "--work_dir",
        default=str(backend_root / ".tmp_kml_roi_infer"),
        help="Temporary work directory",
    )
    parser.add_argument("--model_id", default="cc-ln/CUGRS", help="MMSeg model id")
    parser.add_argument("--device", default="auto", help="Inference device")
    parser.add_argument("--limit", type=int, default=0, help="Process first N polygons only")
    parser.add_argument("--keep_workdir", action="store_true", help="Keep work directory")
    parser.add_argument("--year", default="", help="Single snapshot year (YYYY). Stores outputs as {FID}+{YYYY}.")
    parser.add_argument("--old_year", default="", help="Old year label (YYYY) for old_tif")
    parser.add_argument("--new_year", default="", help="New year label (YYYY) for new_tif")
    args = parser.parse_args()

    old_tif = Path(args.old_tif).expanduser().resolve()
    new_tif = Path(args.new_tif).expanduser().resolve()
    kml_path = Path(args.kml).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve()
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
    worker_runtime = summary.pop("inference_runtime", {})
    if isinstance(worker_runtime, dict):
        runtime.update({key: value for key, value in worker_runtime.items() if value is not None})
    runtime["duration_seconds"] = round(time.monotonic() - started_at, 3)
    summary["runtime"] = runtime
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

