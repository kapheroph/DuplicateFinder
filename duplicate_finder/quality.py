from __future__ import annotations

from dataclasses import dataclass
from math import log1p
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps, ImageStat

from .models import DuplicateGroup, ImageRecord


@dataclass(frozen=True, slots=True)
class ImageQuality:
    path: Path
    width: int
    height: int
    brightness: float
    sharpness: float

    @property
    def pixels(self) -> int:
        return self.width * self.height

    @property
    def megapixels(self) -> float:
        return self.pixels / 1_000_000

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height else 0.0


@dataclass(frozen=True, slots=True)
class GroupAdvice:
    summary: str
    suggestion: Path | None
    suggestion_reason: str | None
    notes: dict[Path, tuple[str, ...]]


def measure_quality(record: ImageRecord) -> ImageQuality:
    """Measure simple, explainable image qualities for review assistance."""
    with Image.open(record.path) as source:
        image = ImageOps.exif_transpose(source).convert("L")
        image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

        brightness = float(ImageStat.Stat(image).mean[0])

        edges = image.filter(ImageFilter.FIND_EDGES)
        stats = ImageStat.Stat(edges)
        sharpness = float(stats.var[0])

    return ImageQuality(
        path=record.path,
        width=record.width,
        height=record.height,
        brightness=brightness,
        sharpness=sharpness,
    )


def _relative_label(value: float, low: float, high: float, label: str) -> str | None:
    if high <= low:
        return None
    span = high - low
    if span < max(abs(high) * 0.10, 1.0):
        return None

    midpoint = (low + high) / 2
    if value >= midpoint:
        return f"{label} than the other image"
    return f"Less {label.lower()} than the other image"


def advise_group(group: DuplicateGroup) -> GroupAdvice:
    """Return cautious, plain-English guidance for a duplicate group."""
    if group.kind == "exact_file":
        return GroupAdvice(
            summary="These files are identical copies. Either one is safe to keep.",
            suggestion=None,
            suggestion_reason=None,
            notes={record.path: ("Identical file contents",) for record in group.files},
        )

    if group.kind == "exact_pixels":
        return GroupAdvice(
            summary=(
                "These files contain the same picture pixel-for-pixel, even though "
                "the files themselves differ. Either image is visually safe to keep."
            ),
            suggestion=None,
            suggestion_reason=None,
            notes={record.path: ("Same visible image",) for record in group.files},
        )

    qualities = [measure_quality(record) for record in group.files]
    by_path = {quality.path: quality for quality in qualities}

    min_pixels = min(q.pixels for q in qualities)
    max_pixels = max(q.pixels for q in qualities)
    min_sharp = min(q.sharpness for q in qualities)
    max_sharp = max(q.sharpness for q in qualities)
    min_bright = min(q.brightness for q in qualities)
    max_bright = max(q.brightness for q in qualities)
    min_ratio = min(q.aspect_ratio for q in qualities)
    max_ratio = max(q.aspect_ratio for q in qualities)

    notes: dict[Path, list[str]] = {record.path: [] for record in group.files}

    if max_pixels > min_pixels * 1.10:
        for quality in qualities:
            if quality.pixels == max_pixels:
                notes[quality.path].append("Higher resolution")
            elif quality.pixels == min_pixels:
                notes[quality.path].append("Lower resolution")

    if max_sharp > max(min_sharp * 1.15, min_sharp + 2.0):
        midpoint = (min_sharp + max_sharp) / 2
        for quality in qualities:
            if quality.sharpness >= midpoint:
                notes[quality.path].append("Looks sharper")
            else:
                notes[quality.path].append("Looks softer")

    if max_bright - min_bright >= 12:
        midpoint = (min_bright + max_bright) / 2
        for quality in qualities:
            if quality.brightness >= midpoint:
                notes[quality.path].append("Brighter")
            else:
                notes[quality.path].append("Darker")

    if max_ratio - min_ratio >= 0.03:
        for quality in qualities:
            notes[quality.path].append("Different framing or crop")

    if not any(notes.values()):
        for quality in qualities:
            notes[quality.path].append("Very similar technical quality")

    pixel_logs = [log1p(q.pixels) for q in qualities]
    sharp_logs = [log1p(max(q.sharpness, 0.0)) for q in qualities]

    def normalise(value: float, values: list[float]) -> float:
        low, high = min(values), max(values)
        if high == low:
            return 0.5
        return (value - low) / (high - low)

    scores: list[tuple[float, ImageQuality]] = []
    for quality, pixel_log, sharp_log in zip(qualities, pixel_logs, sharp_logs):
        score = (
            0.60 * normalise(pixel_log, pixel_logs)
            + 0.40 * normalise(sharp_log, sharp_logs)
        )
        scores.append((score, quality))

    scores.sort(key=lambda item: item[0], reverse=True)
    suggestion: Path | None = None
    suggestion_reason: str | None = None

    if len(scores) >= 2 and scores[0][0] - scores[1][0] >= 0.15:
        winner = scores[0][1]
        suggestion = winner.path

        reasons: list[str] = []
        if winner.pixels >= max_pixels:
            reasons.append("higher resolution")
        if winner.sharpness >= (min_sharp + max_sharp) / 2 and max_sharp > min_sharp * 1.15:
            reasons.append("sharper detail")

        suggestion_reason = (
            "Suggested keep because it has " + " and ".join(reasons)
            if reasons
            else "Suggested keep based on stronger technical quality"
        )

    summary = (
        "These look like the same or closely related photo, but they are not identical. "
        "The notes below highlight measurable differences."
    )

    return GroupAdvice(
        summary=summary,
        suggestion=suggestion,
        suggestion_reason=suggestion_reason,
        notes={path: tuple(items) for path, items in notes.items()},
    )
