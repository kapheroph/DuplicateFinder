from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .scanner import IMAGE_EXTENSIONS


QUARANTINE_DIR_NAME = "DuplicateFinder_Quarantine"


@dataclass(frozen=True, slots=True)
class QuarantineMove:
    source: Path
    destination: Path


def quarantine_directory(scan_root: Path) -> Path:
    """Return the quarantine directory beside the scanned files."""
    return scan_root.expanduser().resolve() / QUARANTINE_DIR_NAME


def unique_destination(directory: Path, filename: str) -> Path:
    """Choose a non-destructive destination without overwriting an existing file."""
    candidate = directory / filename
    if not candidate.exists():
        return candidate

    source = Path(filename)
    stem = source.stem
    suffix = source.suffix
    counter = 2
    while True:
        candidate = directory / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def move_to_quarantine(paths: list[Path], scan_root: Path) -> list[QuarantineMove]:
    """Move selected files into a quarantine folder, never overwriting files."""
    root = scan_root.expanduser().resolve()
    quarantine = quarantine_directory(root)
    quarantine.mkdir(parents=True, exist_ok=True)

    moves: list[QuarantineMove] = []
    for source in paths:
        source = source.expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(source)

        try:
            source.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Refusing to move file outside scan root: {source}") from exc

        if quarantine in source.parents:
            continue

        destination = unique_destination(quarantine, source.name)
        shutil.move(str(source), str(destination))
        moves.append(QuarantineMove(source=source, destination=destination))

    return moves


def list_quarantined_images(scan_root: Path) -> list[Path]:
    """Return supported image files currently held in quarantine."""
    quarantine = quarantine_directory(scan_root)
    if not quarantine.exists():
        return []

    return sorted(
        (
            path
            for path in quarantine.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ),
        key=lambda path: path.name.casefold(),
    )


def restore_from_quarantine(paths: list[Path], scan_root: Path) -> list[QuarantineMove]:
    """Restore selected quarantine files to the scan root without overwriting."""
    root = scan_root.expanduser().resolve()
    quarantine = quarantine_directory(root)

    moves: list[QuarantineMove] = []
    for source in paths:
        source = source.expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(source)

        try:
            source.relative_to(quarantine)
        except ValueError as exc:
            raise ValueError(f"Refusing to restore file outside quarantine: {source}") from exc

        destination = unique_destination(root, source.name)
        shutil.move(str(source), str(destination))
        moves.append(QuarantineMove(source=source, destination=destination))

    return moves
