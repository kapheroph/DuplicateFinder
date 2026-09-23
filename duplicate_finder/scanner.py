from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .actions import QUARANTINE_DIR_NAME

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

    def is_candidate(path: Path) -> bool:
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            return False

        if recursive:
            relative_parts = path.relative_to(folder).parts[:-1]
            if QUARANTINE_DIR_NAME in relative_parts:
                return False

        return True

    return sorted(
        (path for path in iterator if is_candidate(path)),
        key=lambda path: str(path).casefold(),
    )
