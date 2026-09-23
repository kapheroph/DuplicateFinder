from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageOps


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _normalised_image(path: Path) -> Image.Image:
    """Load an image, apply EXIF orientation, and normalise to RGBA pixels."""
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        image.load()
        return image.convert("RGBA")


def pixel_sha256(path: Path) -> tuple[str, int, int]:
    """Hash decoded pixels, independent of file metadata/compression."""
    image = _normalised_image(path)
    digest = hashlib.sha256()
    digest.update(image.width.to_bytes(8, "big"))
    digest.update(image.height.to_bytes(8, "big"))
    digest.update(image.tobytes())
    return digest.hexdigest(), image.width, image.height


def difference_hash(path: Path, hash_size: int = 8) -> int:
    """Return a compact dHash suitable for near-duplicate comparison."""
    image = _normalised_image(path).convert("L")
    image = image.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = image.tobytes()

    value = 0
    row_width = hash_size + 1
    for y in range(hash_size):
        row = y * row_width
        for x in range(hash_size):
            value <<= 1
            value |= pixels[row + x] > pixels[row + x + 1]
    return value


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()
