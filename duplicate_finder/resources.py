from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str | Path) -> Path:
    """Resolve a bundled PyInstaller resource or a source-tree resource."""
    relative = Path(relative_path)

    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / relative

    return Path(__file__).resolve().parent.parent / relative
