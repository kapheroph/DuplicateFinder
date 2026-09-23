from pathlib import Path

import pytest

from duplicate_finder.actions import (
    list_quarantined_images,
    move_to_quarantine,
    quarantine_directory,
    restore_from_quarantine,
)


def test_move_to_quarantine_moves_file_without_deleting(tmp_path: Path) -> None:
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"photo-data")

    moves = move_to_quarantine([source], tmp_path)

    assert len(moves) == 1
    assert not source.exists()
    assert moves[0].destination.exists()
    assert moves[0].destination.parent == quarantine_directory(tmp_path)
    assert moves[0].destination.read_bytes() == b"photo-data"


def test_move_to_quarantine_never_overwrites_existing_file(tmp_path: Path) -> None:
    quarantine = quarantine_directory(tmp_path)
    quarantine.mkdir()
    (quarantine / "photo.jpg").write_bytes(b"existing")

    source = tmp_path / "photo.jpg"
    source.write_bytes(b"new")

    moves = move_to_quarantine([source], tmp_path)

    assert moves[0].destination.name == "photo (2).jpg"
    assert (quarantine / "photo.jpg").read_bytes() == b"existing"
    assert moves[0].destination.read_bytes() == b"new"


def test_move_to_quarantine_rejects_file_outside_scan_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"outside")

    with pytest.raises(ValueError):
        move_to_quarantine([outside], root)

    assert outside.exists()


def test_list_quarantined_images_returns_supported_images(tmp_path: Path) -> None:
    quarantine = quarantine_directory(tmp_path)
    quarantine.mkdir()
    (quarantine / "b.jpg").write_bytes(b"b")
    (quarantine / "a.png").write_bytes(b"a")
    (quarantine / "notes.txt").write_text("ignore", encoding="utf-8")

    found = list_quarantined_images(tmp_path)

    assert [path.name for path in found] == ["a.png", "b.jpg"]


def test_restore_from_quarantine_moves_back_to_scan_root(tmp_path: Path) -> None:
    quarantine = quarantine_directory(tmp_path)
    quarantine.mkdir()
    source = quarantine / "photo.jpg"
    source.write_bytes(b"photo")

    moves = restore_from_quarantine([source], tmp_path)

    assert len(moves) == 1
    assert not source.exists()
    assert moves[0].destination == tmp_path / "photo.jpg"
    assert moves[0].destination.read_bytes() == b"photo"


def test_restore_from_quarantine_never_overwrites_existing_file(tmp_path: Path) -> None:
    (tmp_path / "photo.jpg").write_bytes(b"existing")
    quarantine = quarantine_directory(tmp_path)
    quarantine.mkdir()
    source = quarantine / "photo.jpg"
    source.write_bytes(b"restored")

    moves = restore_from_quarantine([source], tmp_path)

    assert moves[0].destination.name == "photo (2).jpg"
    assert (tmp_path / "photo.jpg").read_bytes() == b"existing"
    assert moves[0].destination.read_bytes() == b"restored"


def test_restore_rejects_file_outside_quarantine(tmp_path: Path) -> None:
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"outside")

    with pytest.raises(ValueError):
        restore_from_quarantine([outside], tmp_path)

    assert outside.exists()
