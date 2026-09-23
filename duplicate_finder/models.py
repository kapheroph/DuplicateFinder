from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ImageRecord:
    path: Path
    size_bytes: int
    file_sha256: str
    pixel_sha256: str
    perceptual_hash: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    kind: str
    files: tuple[ImageRecord, ...]
    distance: int | None = None
