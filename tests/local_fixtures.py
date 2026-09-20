from __future__ import annotations

import unittest
from pathlib import Path


def require_local_fixture(path: Path) -> Path:
    """Return a local-only fixture path or skip the importing test module."""
    if not path.exists():
        raise unittest.SkipTest(f"Local copyrighted fixture not available: {path}")
    return path
