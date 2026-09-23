from __future__ import annotations

from pathlib import Path
from typing import Iterable

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"
}


def scan_images(folder: Path, recursive: bool = True) -> list[Path]:
    """Return supported image files beneath *folder* in deterministic order."""
    folder = folder.expanduser().resolve()
    if not folder.exists():
        raise FileNotFoundError(folder)
    if not folder.is_dir():
        raise NotADirectoryError(folder)

    iterator: Iterable[Path] = folder.rglob("*") if recursive else folder.iterdir()
    return sorted(
        (path for path in iterator if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda path: str(path).casefold(),
    )
