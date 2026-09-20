from __future__ import annotations

from pathlib import Path
import hashlib
import json

from tools.localization import DcLocalization
from tools.mtx import MtxFile, MtxReplacement


ROOT = Path(__file__).parents[1]
fixture = ROOT / "fixtures" / "DG00_00"
raw = (fixture / "original.MTX").read_bytes()
dc = json.loads((fixture / "en.mtxdc.json").read_text())
localization = DcLocalization.from_json(raw, dc)
mtx = MtxFile.parse(raw)
replacements = tuple(
    MtxReplacement(group.anchor, group.replace_end, group.encoded_replacement())
    for group in localization.groups
)
rebuilt = mtx.apply_replacements(replacements).compile()
out = ROOT / "artifacts" / "DG00_00.en-fullwidth.MTX"
out.write_bytes(rebuilt)
parsed = MtxFile.parse(rebuilt)

print(f"original_size={len(raw)}")
print(f"translated_size={len(rebuilt)}")
print(f"delta={len(rebuilt) - len(raw)}")
print(f"original_ptrs={mtx.pointer_offsets}")
print(f"translated_ptrs={parsed.pointer_offsets}")
print(f"sha256={hashlib.sha256(rebuilt).hexdigest()}")
for marker in (b"wc", b"ds01", b"sbr"):
    print(f"{marker.decode()}={raw.count(marker)}->{rebuilt.count(marker)}")
print(f"output={out}")
