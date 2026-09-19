import re
import shutil
import argparse
from pathlib import Path

from applications.kml_roi.tiles import cleanup_output_dir

# 整图（未联动）产物目录名：U + 毫秒时间戳，与主循环防护同一正则
UNLINKED_DIR_PATTERN = re.compile(r"^U[1-9][0-9]*$")


def prune_unlinked_dirs(root: Path, keep: int) -> int:
    """B6（2026-09-19 审查）：整图 U 产物 GB 级/次且此前无清理出口——
    按 mtime 仅保留最近 keep 个 U 目录，其余整目录删除。keep<=0 不动。
    返回删除的目录个数。"""
    if keep <= 0:
        return 0
    dirs = [p for p in root.iterdir() if p.is_dir() and UNLINKED_DIR_PATTERN.match(p.name)]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    removed = 0
    for p in dirs[keep:]:
        shutil.rmtree(p, ignore_errors=True)
        removed += 1
    return removed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output_root", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--fid", default="")
    ap.add_argument("--keep_last_years", type=int, default=3)
    ap.add_argument(
        "--prune-unlinked", type=int, default=0, metavar="N",
        help="按 mtime 仅保留最近 N 个整图（U 前缀）产物目录；0=不动（默认）",
    )
    args = ap.parse_args()

    root = Path(args.output_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(str(root))

    removed_total = 0
    visited = 0

    if args.fid:
        # B7（2026-09-19 审查）：--fid 显式传 U 名此前无守卫，会按普通 fid
        # 清掉整图产物——与主循环同一 ^U 正则防护；清整图请用 --prune-unlinked
        if UNLINKED_DIR_PATTERN.match(str(args.fid)):
            raise ValueError(
                f"--fid 不接受整图产物目录名（U 前缀）: {args.fid}；清理整图产物请用 --prune-unlinked N"
            )
        d = root / str(args.fid)
        if d.exists() and d.is_dir():
            removed_total += cleanup_output_dir(str(args.fid), d, keep_last_years=args.keep_last_years)
            visited = 1
        print({"visited": visited, "removed": removed_total})
        return 0

    removed_total += prune_unlinked_dirs(root, args.prune_unlinked)

    for d in sorted([p for p in root.iterdir() if p.is_dir() and not UNLINKED_DIR_PATTERN.match(p.name)], key=lambda p: p.name):
        fid = d.name
        removed_total += cleanup_output_dir(fid, d, keep_last_years=args.keep_last_years)
        visited += 1
        if args.limit and visited >= args.limit:
            break

    print({"visited": visited, "removed": removed_total})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
