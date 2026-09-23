from __future__ import annotations

import argparse
from pathlib import Path

from .duplicates import AnalysisResult, analyze_folder


def _print_group(title: str, groups) -> None:
    print(f"\n{title}: {len(groups)}")
    for number, group in enumerate(groups, 1):
        suffix = f" (max dHash distance {group.distance})" if group.distance is not None else ""
        print(f"  Group {number}{suffix}")
        for record in group.files:
            print(f"    {record.path}")


def print_result(result: AnalysisResult) -> None:
    print(f"Folder: {result.folder}")
    print(f"Images scanned: {result.images_scanned}")
    _print_group("Exact file duplicate groups", result.exact_file_groups)
    _print_group("Exact pixel duplicate groups", result.exact_pixel_groups)
    _print_group("Near-duplicate groups", result.near_duplicate_groups)

    if result.unreadable:
        print(f"\nUnreadable/skipped: {len(result.unreadable)}")
        for path, error in result.unreadable:
            print(f"  {path}: {error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="duplicate-finder",
        description="Find exact and visually near-duplicate images in a folder.",
    )
    parser.add_argument("folder", type=Path, help="Folder containing images to scan")
    parser.add_argument("--no-recursive", action="store_true", help="Do not scan subfolders")
    parser.add_argument(
        "--near-threshold",
        type=int,
        default=6,
        help="Maximum dHash Hamming distance for near duplicates (default: 6)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = analyze_folder(
        args.folder,
        recursive=not args.no_recursive,
        near_threshold=args.near_threshold,
    )
    print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
