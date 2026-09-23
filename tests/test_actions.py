from pathlib import Path

import pytest

from duplicate_finder.actions import move_to_quarantine, quarantine_directory


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
