from __future__ import annotations

import hashlib
from pathlib import Path

from tools.early_ui import EARLY_UI_PATCHES, build_early_ui_elf


ROOT = Path(__file__).parents[1]
source = ROOT / "fixtures" / "elf" / "SLPM_665.11"
out = ROOT / "artifacts" / "SLPM_665.11.en-early"

raw = source.read_bytes()
patched = build_early_ui_elf(raw)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(patched)

diff_count = sum(a != b for a, b in zip(raw, patched))
print(f"source={source}")
print(f"output={out}")
print(f"size={len(patched)} unchanged={len(raw) == len(patched)}")
print(f"patches={len(EARLY_UI_PATCHES)} changed_bytes={diff_count}")
print(f"sha256_before={hashlib.sha256(raw).hexdigest()}")
print(f"sha256_after={hashlib.sha256(patched).hexdigest()}")
for patch in EARLY_UI_PATCHES:
    print(f"{patch.offset:#010x} {patch.expected!r} -> {patch.text!r}")
