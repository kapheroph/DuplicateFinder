# DuplicateFinder

A small, non-destructive image duplicate finder intended to grow into a simple Windows desktop app.

## Milestone 1: duplicate-detection core

The current core scans a folder recursively and reports three useful categories:

- **Exact file duplicates** — identical file bytes using SHA-256.
- **Exact pixel duplicates** — decoded image pixels are identical even when metadata or compression differs.
- **Near duplicates** — visually similar images using a compact difference hash (dHash).

Nothing is moved or deleted.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python main.py "D:\Photos"
```

Optional controls:

```powershell
python main.py "D:\Photos" --near-threshold 6
python main.py "D:\Photos" --no-recursive
```

A lower near-duplicate threshold is stricter. The default is `6`.

## Tests

```powershell
pytest
```

## Planned next step

Add a PySide6 desktop frontend with folder selection, progress, thumbnail groups, side-by-side review, and safe quarantine actions. Permanent deletion will not be the default behavior.
