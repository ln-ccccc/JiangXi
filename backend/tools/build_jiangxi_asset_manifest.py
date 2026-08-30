from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from tools.validate_jiangxi_assets import (
    _build_parser as _build_asset_parser,
    default_asset_paths,
    validate_jiangxi_assets,
)


def _build_parser():
    parser = _build_asset_parser()
    parser.add_argument("--output", default=str(Path("docker/standalone/runtime_data/Jiangxi_asset_manifest.json")))
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    explicit_paths = any(flag in (argv or sys.argv[1:]) for flag in ("--excel", "--shp", "--kmz", "--csv"))
    report = validate_jiangxi_assets(
        args.excel,
        args.shp,
        args.kmz,
        args.csv,
        expected_count=args.expected_count if args.expected_count is not None else (None if explicit_paths else 348),
        manifest_path=None,
    )
    for entry in report.get("files", {}).values():
        entry["path"] = Path(entry["path"]).name
    manifest = {
        "source": "jiangxi-runtime-assets",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **report,
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
