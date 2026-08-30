import argparse
import json
import os
from pathlib import Path

from applications import create_app
from applications.project_hub.jiangxi_seed_service import (
    seed_jiangxi_project_from_csv,
    sync_jiangxi_project_from_workbook,
)


def build_parser():
    parser = argparse.ArgumentParser(description="清空项目业务库并从 Mine.csv 重建江西默认项目。")
    parser.add_argument(
        "--csv-path",
        default="/app/runtime_data/Mine.csv",
        help="Mine.csv 的路径，默认使用单镜像运行时目录。",
    )
    parser.add_argument(
        "--config",
        default=os.getenv("FLASK_CONFIG", "production"),
        choices=["development", "testing", "production"],
        help="Flask 配置名，默认 production。",
    )
    parser.add_argument(
        "--actor",
        default="cli",
        help="写入项目活动日志的执行人标识，默认 cli。",
    )
    parser.add_argument(
        "--workbook-path",
        default=None,
        help="348 图斑 TableMERNet 工作簿路径；提供后以图斑粒度建立默认项目台账。",
    )
    parser.add_argument(
        "--manifest",
        default=os.getenv("JIANGXI_ASSET_MANIFEST_PATH"),
        help="江西权威资产 manifest 路径；发布模式必须提供。",
    )
    parser.add_argument(
        "--sync-existing",
        action="store_true",
        help="仅对齐现有江西默认项目，不清空项目、数据集或导出记录。",
    )
    return parser


def main():
    args = build_parser().parse_args()
    app = create_app(args.config)
    csv_path = Path(args.csv_path).expanduser().resolve()
    with app.app_context():
        if args.sync_existing:
            if not args.workbook_path:
                parser.error("--sync-existing 必须同时提供 --workbook-path")
            result = sync_jiangxi_project_from_workbook(
                args.workbook_path,
                actor=args.actor,
                manifest_path=args.manifest,
            )
        else:
            result = seed_jiangxi_project_from_csv(
                csv_path,
                actor=args.actor,
                workbook_path=args.workbook_path,
                manifest_path=args.manifest,
            )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
