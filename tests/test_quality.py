from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from duplicate_finder.models import DuplicateGroup, ImageRecord
from duplicate_finder.quality import advise_group


def _record(path: Path) -> ImageRecord:
    with Image.open(path) as image:
        width, height = image.size

    return ImageRecord(
        path=path,
        size_bytes=path.stat().st_size,
        file_sha256=path.name,
        pixel_sha256=f"pixels-{path.name}",
        perceptual_hash=0,
        width=width,
        height=height,
    )


def test_exact_file_advice_says_either_is_safe(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    Image.new("RGB", (20, 20), "white").save(first)
    Image.new("RGB", (20, 20), "white").save(second)

    group = DuplicateGroup(
        kind="exact_file",
        files=(_record(first), _record(second)),
    )

    advice = advise_group(group)

    assert "Either one is safe to keep" in advice.summary
    assert advice.suggestion is None


def test_similar_group_prefers_larger_sharper_image(tmp_path: Path) -> None:
    large = tmp_path / "large.png"
    small_soft = tmp_path / "small_soft.png"

    image = Image.new("L", (300, 300), 220)
    draw = ImageDraw.Draw(image)
    for x in range(20, 280, 20):
        draw.line((x, 20, x, 280), fill=30, width=3)
        draw.line((20, x, 280, x), fill=30, width=3)
    image.save(large)

    image.resize((120, 120), Image.Resampling.LANCZOS).filter(
        ImageFilter.GaussianBlur(2.5)
    ).save(small_soft)

    group = DuplicateGroup(
        kind="near",
        files=(_record(large), _record(small_soft)),
        distance=4,
    )

    advice = advise_group(group)

    assert advice.suggestion == large
    assert any("Higher resolution" in note for note in advice.notes[large])
    assert any("Looks sharper" in note for note in advice.notes[large])


def test_similar_group_reports_brightness_difference(tmp_path: Path) -> None:
    bright = tmp_path / "bright.png"
    dark = tmp_path / "dark.png"

    Image.new("L", (100, 100), 210).save(bright)
    Image.new("L", (100, 100), 80).save(dark)

    group = DuplicateGroup(
        kind="near",
        files=(_record(bright), _record(dark)),
        distance=3,
    )

    advice = advise_group(group)

    assert "Brighter" in advice.notes[bright]
    assert "Darker" in advice.notes[dark]
