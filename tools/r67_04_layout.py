"""67.04 conservative user-reported fixes on 67.03, preserving accepted UI.

The correction is intentionally limited to the first 15 Basic Attack text rows
and one independent fixed-width rotation prompt. The exact official item names
are immutable: the acceptance gate forbids shortening them. Do not touch the
unverified story-comment renderers or the already accepted Turn-Based Combat.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.first_save_help import _icon_reservations, _metadata, _MAX_CELLS
from tools.inspect_english_bytes import parse
from tools.localization import encode_ps2_english

BASE_SHA = "1913153bc67d4b2febc444cedfa5fb62fdc5aeaed94d077762416f3688cb24a8"
NATIVE_ROTATE_SLOT = 0x596CD0
ROTATE_SLOT_SIZE = 32
ROTATE_JAPANESE = "ターゲットの変更"
ROTATE_ENGLISH = "Change target"

# Exactly 15 original populated rows. The following 7 native blank rows,
# their icon positions and the page EOF are frozen; rewriting them froze Help
# in an earlier candidate. Controller icon sprite holes are preserved.
BASIC_ATTACK = (
    "Basic Attack", "",
    "1. Approach the enemy.", "",
    "2. Ready a weapon.",
    "Press          to equip.",
    "3. Aim at the enemy.",
    "Use the R Stick to aim.",
    "        Select target.",
    "4. Fire your weapon.",
    "Attacks consume AP.", "",
    "5. End your turn.",
    "When AP is depleted,",
    "wait until next turn.",
)

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def payload(text: str) -> bytes:
    return encode_ps2_english(text, collapse_spaces=False) + b"\0"

def _resolve(elf: bytes, va: int) -> int:
    segment_offset, segment_va = struct.unpack_from("<II", elf, 0x58)
    off = segment_offset + va - segment_va
    if not segment_offset <= off < len(elf):
        raise ValueError("Translation pointer is outside the ELF PT_LOAD")
    return off

def apply(pristine: bytes, prior: bytes, english_rows: list, pages: list) -> tuple[bytes, dict]:
    if sha(prior) != BASE_SHA:
        raise ValueError("67.03 ELF fingerprint changed")
    original = pristine[NATIVE_ROTATE_SLOT:NATIVE_ROTATE_SLOT + ROTATE_SLOT_SIZE]
    jp = ROTATE_JAPANESE.encode("cp932") + b"\0"
    if not original.startswith(jp) or original[len(jp):] != b"\0" * (ROTATE_SLOT_SIZE - len(jp)):
        raise ValueError("Native rotate slot layout changed")
    if prior[NATIVE_ROTATE_SLOT:NATIVE_ROTATE_SLOT + ROTATE_SLOT_SIZE] != original:
        raise ValueError("Rotation prompt already modified")
    official = {en for jp_text, en, _ in english_rows if jp_text == ROTATE_JAPANESE}
    if official != {ROTATE_ENGLISH}:
        raise ValueError("PS4 official rotation translation drifted")
    result = bytearray(prior)
    whitelist: set[int] = set(range(0x64, 0x68))
    rotation = payload(ROTATE_ENGLISH)
    if len(rotation) > ROTATE_SLOT_SIZE:
        raise ValueError("Rotation label exceeds fixed 32-byte slot")
    result[NATIVE_ROTATE_SLOT:NATIVE_ROTATE_SLOT + ROTATE_SLOT_SIZE] = rotation.ljust(ROTATE_SLOT_SIZE, b"\0")
    whitelist.update(range(NATIVE_ROTATE_SLOT, NATIVE_ROTATE_SLOT + ROTATE_SLOT_SIZE))

    def append(text: str) -> int:
        if len(result) & 1:
            result.append(0)
        offset, va = struct.unpack_from("<II", prior, 0x58)
        ptr = va + len(result) - offset
        result.extend(payload(text))
        return ptr

    page = next(p for p in pages if p["key"] == "basic_attack")
    if len(BASIC_ATTACK) != 15 or page["rows"] != 22:
        raise ValueError("Basic Attack row count changed")
    reserved, _ = _icon_reservations(page, _metadata(pristine, page))
    descriptor = page["descriptor_offset"]
    table = _resolve(prior, struct.unpack_from("<I", prior, descriptor)[0])
    original_blank_rows = prior[table + 15*4:table + (page["rows"] + 1)*4]
    if any(struct.unpack_from("<I", original_blank_rows, k)[0] != 0x795FB8
           for k in range(0, 7*4, 4)):
        raise ValueError("Native Basic Attack blank row sentinels changed")
    if struct.unpack_from("<I", original_blank_rows, 7*4)[0] != 0x795FBC:
        raise ValueError("Native Basic Attack EOF changed")

    edits = []
    for row, text in enumerate(BASIC_ATTACK):
        if len(text) > _MAX_CELLS or any(c < len(text) and text[c] != " " for c in reserved[row]):
            raise ValueError(f"Basic Attack text overlaps native icon row {row}")
        pos = table + row*4
        old_ptr = struct.unpack_from("<I", prior, pos)[0]
        old_offset = _resolve(prior, old_ptr)
        if prior.find(b"\0", old_offset, old_offset+256) < 0:
            raise ValueError("Corrupt original Help text row")
        target = append(text)
        struct.pack_into("<I", result, pos, target)
        whitelist.update(range(pos, pos+4))
        edits.append({"row": row, "text": text, "owner": hex(pos)})
    if result[table + 15*4:table + (page["rows"] + 1)*4] != original_blank_rows:
        raise ValueError("Basic Attack blank icon rows changed")
    for label in ("turn_based_combat", "entering_battle"):
        immutable = next(p for p in pages if p["key"] == label)
        for field, size in (("descriptor_offset", 4), ("metadata_descriptor_offset", 4)):
            where = immutable[field]
            if result[where:where+size] != prior[where:where+size]:
                raise ValueError(f"Accepted {label} descriptor changed")
        t = _resolve(prior, struct.unpack_from("<I", prior, immutable["descriptor_offset"])[0])
        size = (immutable["rows"] + 1)*4
        if result[t:t+size] != prior[t:t+size]:
            raise ValueError(f"Accepted {label} row table changed")
    fo, va, size, reserve, flags = (struct.unpack_from("<I", prior, i)[0]
                                   for i in (0x58, 0x5C, 0x64, 0x68, 0x6C))
    if flags != 7 or fo+size != len(prior) or len(result)-fo > reserve:
        raise ValueError("Translation PT_LOAD identity/budget changed")
    struct.pack_into("<I", result, 0x64, len(result)-fo)
    for i,(old,new) in enumerate(zip(prior,result)):
        if old != new and i not in whitelist:
            raise ValueError(f"Unexpected 67.04 change at {i:#x}")
    return bytes(result), {
        "prior_sha256": sha(prior), "sha256": sha(result),
        "previous_size": len(prior), "new_size": len(result),
        "appended_bytes": len(result)-len(prior),
        "fixed_slot": [NATIVE_ROTATE_SLOT, ROTATE_SLOT_SIZE, ROTATE_ENGLISH],
        "basic_attack_rows": edits,
        "locked_turn_based_combat": True,
        "renderer_geometry_modified": False,
        "save_namespace_modified": False,
        "open_runtime_issues": [
            "START dialogue-history orientation",
            "Old-man story comment bubble/text mismatch",
            "Use Item right edge inset",
        ],
    }

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("pristine", "baseline", "official", "manifest", "output", "report"):
        p.add_argument("--"+name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists() or a.report.exists():
        raise FileExistsError("Refusing overwrite")
    result, report = apply(
        a.pristine.read_bytes(), a.baseline.read_bytes(),
        parse(a.official), json.loads(a.manifest.read_text())["pages"],
    )
    a.output.write_bytes(result)
    a.report.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("basic_attack_rows",)},indent=2))
if __name__ == "__main__":
    main()
