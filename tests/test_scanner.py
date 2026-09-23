from pathlib import Path

from PIL import Image

from duplicate_finder.actions import quarantine_directory
from duplicate_finder.scanner import scan_images


def test_scan_images_is_recursive_and_ignores_other_files(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    Image.new("RGB", (4, 4), "red").save(tmp_path / "one.png")
    Image.new("RGB", (4, 4), "blue").save(nested / "two.jpg")
    (nested / "notes.txt").write_text("not an image", encoding="utf-8")

    found = scan_images(tmp_path)

    assert {path.name for path in found} == {"one.png", "two.jpg"}


def test_recursive_scan_ignores_quarantine_folder(tmp_path: Path) -> None:
    Image.new("RGB", (4, 4), "red").save(tmp_path / "keep.png")

    quarantine = quarantine_directory(tmp_path)
    quarantine.mkdir()
    Image.new("RGB", (4, 4), "blue").save(quarantine / "quarantined.png")

    found = scan_images(tmp_path, recursive=True)

    assert [path.name for path in found] == ["keep.png"]
