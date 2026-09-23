from pathlib import Path

from PIL import Image, PngImagePlugin

from duplicate_finder.hashing import hamming_distance, pixel_sha256, sha256_file


def test_same_pixels_ignore_png_metadata(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    image = Image.new("RGB", (16, 16), (20, 40, 60))
    image.save(first)

    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Comment", "different file bytes")
    image.save(second, pnginfo=metadata)

    assert sha256_file(first) != sha256_file(second)
    assert pixel_sha256(first)[0] == pixel_sha256(second)[0]


def test_hamming_distance() -> None:
    assert hamming_distance(0b0000, 0b1111) == 4
    assert hamming_distance(0b1010, 0b1011) == 1
