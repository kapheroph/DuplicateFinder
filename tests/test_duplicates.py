from pathlib import Path
import shutil

from PIL import Image, ImageDraw, PngImagePlugin

from duplicate_finder.duplicates import analyze_folder


def _pattern(path: Path, *, offset: int = 0, metadata: bool = False) -> None:
    image = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((8 + offset, 8, 40 + offset, 40), fill="black")
    if metadata:
        info = PngImagePlugin.PngInfo()
        info.add_text("Comment", "metadata variant")
        image.save(path, pnginfo=info)
    else:
        image.save(path)


def test_analyze_folder_separates_duplicate_types(tmp_path: Path) -> None:
    original = tmp_path / "original.png"
    byte_copy = tmp_path / "byte_copy.png"
    pixel_copy = tmp_path / "pixel_copy.png"
    near = tmp_path / "near.png"
    different = tmp_path / "different.png"

    _pattern(original)
    shutil.copyfile(original, byte_copy)
    _pattern(pixel_copy, metadata=True)
    _pattern(near, offset=2)
    Image.new("RGB", (64, 64), "blue").save(different)

    result = analyze_folder(tmp_path, near_threshold=10)

    assert result.images_scanned == 5
    assert len(result.exact_file_groups) == 1
    assert {p.path.name for p in result.exact_file_groups[0].files} == {
        "original.png", "byte_copy.png"
    }

    assert len(result.exact_pixel_groups) == 1
    assert {p.path.name for p in result.exact_pixel_groups[0].files} == {
        "original.png", "byte_copy.png", "pixel_copy.png"
    }

    near_names = [
        {record.path.name for record in group.files}
        for group in result.near_duplicate_groups
    ]
    assert any("near.png" in names and "original.png" in names for names in near_names)
