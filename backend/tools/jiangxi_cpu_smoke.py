"""Run one deterministic CPU inference and write an auditable result manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from applications.interface.mmseg_inference_caller import _run_mmseg_inference, get_model_paths
from applications.project_hub.tbbh_identity import normalize_tbbh


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_identity(manifest_path: Path, requested_tbbh: str | None):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "ok":
        raise RuntimeError("江西资产 manifest 状态不是 ok")
    mapping = {
        normalize_tbbh(tbbh): int(map_fid)
        for tbbh, map_fid in (manifest.get("mapping", {}).get("tbbh_to_map_fid") or {}).items()
    }
    if not mapping:
        raise RuntimeError("江西资产 manifest 缺少 TBBH/map_fid 映射")
    tbbh = normalize_tbbh(requested_tbbh) if requested_tbbh else sorted(mapping)[0]
    if tbbh not in mapping:
        raise RuntimeError(f"TBBH 不在江西资产 manifest: {tbbh}")
    return manifest, tbbh, mapping[tbbh]


def _build_parser():
    return argparse.ArgumentParser(description="江西模型单影像 CPU 推理烟囱测试")


def main(argv=None) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    runtime_root = repo_root / "docker" / "standalone" / "runtime_data"
    parser = _build_parser()
    parser.add_argument("--input-image", default=str(repo_root / "backend" / "test.tif"))
    parser.add_argument("--output-dir", default=str(runtime_root / "inference_smoke"))
    parser.add_argument(
        "--manifest",
        default=os.getenv("JIANGXI_ASSET_MANIFEST_PATH") or str(runtime_root / "Jiangxi_asset_manifest.json"),
    )
    parser.add_argument("--tbbh", default=None)
    args = parser.parse_args(argv)

    input_path = Path(args.input_image).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"固定测试影像不存在: {input_path}")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"江西资产 manifest 不存在: {manifest_path}")

    manifest, tbbh, map_fid = _load_identity(manifest_path, args.tbbh)
    config_path, checkpoint_path = get_model_paths("cc-ln/CUGRS")
    output_dir.mkdir(parents=True, exist_ok=True)
    result = _run_mmseg_inference(
        model_id="cc-ln/CUGRS",
        data_path=str(input_path.parent),
        out_dir=str(output_dir),
        names=[input_path.name],
        device="cpu",
    )
    results = result.get("results") or []
    successful = [item for item in results if item.get("status") == "success"]
    if len(successful) != 1:
        raise RuntimeError(f"CPU 推理未得到唯一成功结果: {result}")
    output_path = output_dir / str(successful[0].get("name") or "")
    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise RuntimeError(f"CPU 推理输出为空: {output_path}")

    metadata_path = Path(os.environ["JIANGXI_MMSEG_METADATA_PATH"]).expanduser().resolve()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    smoke_manifest = {
        "status": "ok",
        "tbbh": tbbh,
        "map_fid": map_fid,
        "source_output_dir": str(output_dir),
        "input_sha256": _sha256(input_path),
        "output_sha256": _sha256(output_path),
        "model_hashes": {
            key: metadata.get(key)
            for key in ("config_sha256", "checkpoint_sha256", "source_sha256")
        },
        "asset_manifest_sha256": _sha256(manifest_path),
        "config_path": str(Path(config_path).resolve()),
        "checkpoint_path": str(Path(checkpoint_path).resolve()),
        "manifest_version": manifest.get("version"),
    }
    manifest_output = output_dir / "inference_smoke_manifest.json"
    manifest_output.write_text(
        json.dumps(smoke_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(smoke_manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
