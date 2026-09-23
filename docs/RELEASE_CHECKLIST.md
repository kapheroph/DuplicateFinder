# Release Checklist

Use this when making a future Bill's Duplicate Finder release.

## 1. Start clean

```powershell
git switch main
git pull
git status
```

The working tree should be clean before release work begins.

## 2. Develop on a branch

Create a feature or release branch rather than working directly on `main`.

Example:

```powershell
git switch -c feature/rotation-tools
```

## 3. Test from source

```powershell
pytest
python gui.py
```

Check a real image folder and exercise the feature you changed.

## 4. Check the safety workflow

Before every release, confirm:

- scanning does not modify images;
- quarantine moves rather than deletes;
- the quarantine folder is excluded from scans;
- restore works;
- restore does not overwrite an existing file;
- there is still no accidental permanent-delete path.

## 5. Merge to main

Open and merge the pull request only after tests and the real-folder smoke test pass.

Then locally:

```powershell
git switch main
git pull
```

## 6. Build the Windows app

```powershell
.\build_windows.ps1
```

Expected output:

```text
dist\Bill's Duplicate Finder.exe
```

Run the built `.exe` itself. Do not treat a successful source run as proof that the PyInstaller build is good.

## 7. Smoke-test the packaged app

Check:

- icon appears correctly;
- app opens without a console window;
- folder chooser works;
- scan completes;
- duplicate cards and advice render correctly;
- larger preview works;
- quarantine and confirmation work;
- Quarantine Manager opens;
- restore works;
- stylesheet is present and the UI has not fallen back to default Qt styling.

## 8. Tag the release

Example for a future v1.1.0:

```powershell
git tag v1.1.0
git push origin v1.1.0
```

Use semantic-style tags such as `v1.0.1`, `v1.1.0`, or `v2.0.0` depending on the size of the change.

## 9. Keep the known-good executable

It is worth keeping a copy of each known-good packaged `.exe` outside the build folder, named with its version, for example:

```text
Bill's Duplicate Finder v1.1.0.exe
```
