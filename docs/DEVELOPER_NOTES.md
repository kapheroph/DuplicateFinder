# Bill's Duplicate Finder - Developer Notes

These notes describe the v1.0 architecture and the safest places to extend it later.

## Project shape

The project is deliberately small and local-only. It has no database, server, cloud service, account system, or telemetry.

Main areas:

- `gui.py` - desktop entry point.
- `duplicate_finder/scanner.py` - finds supported image files and excludes the quarantine folder.
- `duplicate_finder/hashing.py` - SHA-256 file hashing, decoded-pixel hashing, dHash, and Hamming distance.
- `duplicate_finder/duplicates.py` - groups exact, same-pixel, and near-duplicate images.
- `duplicate_finder/models.py` - core dataclasses.
- `duplicate_finder/actions.py` - quarantine and restore operations.
- `duplicate_finder/quality.py` - explainable technical comparisons for similar images.
- `duplicate_finder/ui/main_window.py` - PySide6 desktop UI.
- `duplicate_finder/ui/styles.qss` - application styling.
- `duplicate_finder/resources.py` - resolves resources both from source and from a PyInstaller bundle.
- `tests/` - scanner, hashing, grouping, quarantine/restore, and quality-advice tests.

## Duplicate detection

### Exact file duplicates

A SHA-256 hash is calculated from the complete file bytes. Matching hashes mean the files are byte-for-byte identical.

### Same-pixel duplicates

Pillow loads each image, applies EXIF orientation, converts it to RGBA, and hashes the decoded dimensions and pixel bytes. This can find visually identical images whose metadata or compression differs.

### Similar images

A 64-bit difference hash (dHash) is calculated using Pillow. Images are compared by Hamming distance. The v1 default near-duplicate threshold is 6.

The near-duplicate grouping uses connectivity: if A is close to B and B is close to C, they may appear in one group even if A and C are not the closest pair. Keep this in mind if the similarity algorithm is changed later.

## Quality guidance

`quality.py` deliberately uses understandable, local measurements rather than a black-box model. It currently considers:

- pixel dimensions / resolution;
- a simple edge-based sharpness measure;
- mean brightness;
- aspect-ratio differences as a hint that framing or crop differs.

For Similar groups, a technical score is weighted toward resolution and sharpness. A `Suggested keep` is shown only when the difference is sufficiently clear. It is intentionally phrased as guidance rather than an automatic decision.

Possible later improvements include better blur detection, perceptual crop/alignment comparison, duplicate-region overlays, or an optional side-by-side difference viewer.

## Safety model

The safety rule for this project is simple:

> Bill's Duplicate Finder does not permanently delete photos.

Quarantine is located at:

`<scan folder>/DuplicateFinder_Quarantine`

Recursive scans exclude this folder.

Quarantine and restore operations never overwrite existing files. If a destination exists, a numbered name such as `photo (2).jpg` is chosen instead.

If quarantine is expanded to preserve nested folder structure in a future release, strongly consider adding a small persistent manifest containing original relative paths. The current v1 workflow is intentionally simple and is best suited to the normal non-recursive use case.

## UI behaviour

- Folder picker defaults to the user's Windows Pictures folder.
- `Include subfolders` defaults to off.
- Scanning runs in a `QThread` so the UI remains responsive.
- Duplicate decisions are stored by image path during the current review session.
- Clicking an image opens a larger preview.
- Quarantine Manager can restore selected images or all images and can open the quarantine folder in Explorer.

## Packaging

Development dependencies are in `requirements-dev.txt` and include PyInstaller.

Build on Windows from the repository root:

```powershell
.\build_windows.ps1
```

Output:

```text
dist\Bill's Duplicate Finder.exe
```

The build is a single-file, windowed executable. The script bundles:

- the app icon at `assets/bills_duplicate_finder.ico`;
- the Qt stylesheet at `duplicate_finder/ui/styles.qss`.

`resource_path()` handles source-tree versus PyInstaller paths.

## Testing before changes are merged

Run:

```powershell
pytest
```

For UI changes, also run:

```powershell
python gui.py
```

Then perform one real-folder smoke test covering:

1. scan;
2. Exact / Same pixels / Similar display;
3. Suggested keep advice;
4. quarantine;
5. automatic rescan;
6. Quarantine Manager;
7. restore;
8. packaged `.exe` after rebuilding.

## Sensible future features

Good candidates that preserve the small-app philosophy:

- manual Rotate Left / Rotate Right;
- image comparison slider or rapid A/B flip;
- clearer crop/alignment comparison;
- optional preserve-original-folder restore manifest for recursive use;
- a small About dialog showing version number;
- installer or shortcut creation if distribution grows beyond one family PC.

Avoid adding a permanent delete button unless the product direction changes deliberately. The current extra friction is a feature, not a limitation.
