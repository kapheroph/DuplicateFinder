from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .hashing import difference_hash, hamming_distance, pixel_sha256, sha256_file
from .models import DuplicateGroup, ImageRecord
from .scanner import scan_images


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    folder: Path
    images_scanned: int
    exact_file_groups: tuple[DuplicateGroup, ...]
    exact_pixel_groups: tuple[DuplicateGroup, ...]
    near_duplicate_groups: tuple[DuplicateGroup, ...]
    unreadable: tuple[tuple[Path, str], ...]


def _build_records(paths: list[Path]) -> tuple[list[ImageRecord], list[tuple[Path, str]]]:
    records: list[ImageRecord] = []
    unreadable: list[tuple[Path, str]] = []

    for path in paths:
        try:
            file_hash = sha256_file(path)
            pixel_hash, width, height = pixel_sha256(path)
            visual_hash = difference_hash(path)
            records.append(
                ImageRecord(
                    path=path,
                    size_bytes=path.stat().st_size,
                    file_sha256=file_hash,
                    pixel_sha256=pixel_hash,
                    perceptual_hash=visual_hash,
                    width=width,
                    height=height,
                )
            )
        except Exception as exc:
            unreadable.append((path, f"{type(exc).__name__}: {exc}"))

    return records, unreadable


def _groups_by(records: list[ImageRecord], attribute: str, kind: str) -> list[DuplicateGroup]:
    buckets: dict[object, list[ImageRecord]] = defaultdict(list)
    for record in records:
        buckets[getattr(record, attribute)].append(record)

    groups = [
        DuplicateGroup(kind=kind, files=tuple(files))
        for files in buckets.values()
        if len(files) > 1
    ]
    return sorted(groups, key=lambda group: str(group.files[0].path).casefold())


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def _near_groups(records: list[ImageRecord], threshold: int) -> list[DuplicateGroup]:
    if threshold < 0:
        raise ValueError("near-duplicate threshold must be >= 0")

    union = _UnionFind(len(records))

    for left in range(len(records)):
        for right in range(left + 1, len(records)):
            if records[left].pixel_sha256 == records[right].pixel_sha256:
                continue

            distance = hamming_distance(
                records[left].perceptual_hash,
                records[right].perceptual_hash,
            )
            if distance <= threshold:
                union.union(left, right)

    components: dict[int, list[int]] = defaultdict(list)
    for index in range(len(records)):
        components[union.find(index)].append(index)

    groups: list[DuplicateGroup] = []
    for indices in components.values():
        if len(indices) < 2:
            continue

        files = tuple(records[index] for index in indices)
        distances = [
            hamming_distance(records[a].perceptual_hash, records[b].perceptual_hash)
            for pos, a in enumerate(indices)
            for b in indices[pos + 1 :]
        ]
        groups.append(
            DuplicateGroup(
                kind="near",
                files=files,
                distance=max(distances),
            )
        )

    return sorted(groups, key=lambda group: str(group.files[0].path).casefold())


def analyze_folder(
    folder: str | Path,
    *,
    recursive: bool = True,
    near_threshold: int = 6,
) -> AnalysisResult:
    root = Path(folder).expanduser().resolve()
    paths = scan_images(root, recursive=recursive)
    records, unreadable = _build_records(paths)

    exact_file = _groups_by(records, "file_sha256", "exact_file")

    pixel_groups = _groups_by(records, "pixel_sha256", "exact_pixels")
    exact_pixels = [
        group
        for group in pixel_groups
        if len({record.file_sha256 for record in group.files}) > 1
    ]

    near = _near_groups(records, near_threshold)

    return AnalysisResult(
        folder=root,
        images_scanned=len(records),
        exact_file_groups=tuple(exact_file),
        exact_pixel_groups=tuple(exact_pixels),
        near_duplicate_groups=tuple(near),
        unreadable=tuple(unreadable),
    )
