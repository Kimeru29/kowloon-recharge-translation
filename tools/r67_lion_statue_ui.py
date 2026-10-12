"""r67.14r: Lion Statue name fit in two independently owned dungeon UI paths.

Intercept only the names passed to the localized text constructor:
* M_ObjGetDraw item-acquisition label (VA 0x2A2A6C).
* M_DngItemUse selection label (VA 0x2A6060).

The wrapper always calls the original native text setter first, then adjusts
ONLY horizontal glyph scale of the resulting text object if the exact approved
Lion Statue catalog-string POINTER was passed. All other items follow the
unmodified native path. No string, background, global renderer or save code
is changed. Visual approval is required; this is a diagnostic, not a release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.localization import encode_ps2_english
from tools.r67_chamber_story_text_only import (
    Assembly, ELF_BIAS, ELF_SEGMENT_FO, ELF_SEGMENT_VA,
    ELF_SEGMENT_RESERVE, _i, _r, _jal, _float_word,
)

APPROVED_ELF_SHA256 = "c3babe784c07f83312273ac789040b74ea46d492eea48eee0f1ae17ce5c781ba"
ITEM_ID = 413
ITEM_NAME = "Lion Statue"
ITEM_NAME_POINTER_OFFSET = 0x3912B4 + ITEM_ID * 4
CALL_SITES = (0x2A2A6C, 0x2A6060)
ORIGINAL_TEXT_SETTER = 0x18A080
NATIVE_XY_SCALING_SETTER = 0x18B120
FIT_HORIZONTAL_SCALE = 0.78
# Exact surrounding instruction ownership fingerprints, including call+delay.
CALL_CONTEXTS: dict[int, tuple[int, ...]] = {
    0x2A2A6C: (
        0x8E040000,  # lw a0,0(s0)
        0x0040282D,  # daddu a1,v0,zero (native move)
        _jal(ORIGINAL_TEXT_SETTER),
        0x00000000,
    ),
    0x2A6060: (
        0x8E04001C,  # lw a0,0x1c(s0)
        0x0040282D,  # daddu a1,v0,zero (native move)
        _jal(ORIGINAL_TEXT_SETTER),
        0x00000000,
    ),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def item_pointer(source: bytes) -> int:
    pointer = struct.unpack_from("<I", source, ITEM_NAME_POINTER_OFFSET)[0]
    off = ELF_SEGMENT_FO + pointer - ELF_SEGMENT_VA
    expected = encode_ps2_english(ITEM_NAME, collapse_spaces=False) + b"\0"
    if not (ELF_SEGMENT_FO <= off < len(source)) or source[off:off + len(expected)] != expected:
        raise ValueError("Official Lion Statue catalog pointer/string was changed")
    return pointer


def make_helper(name_ptr: int) -> bytes:
    m = Assembly()
    m.emit(_i(9, 29, 29, -0x30))    # stack, 48-byte 16-aligned frame
    m.emit(_i(63, 29, 31, 0x20))   # sd ra,32(sp)
    m.emit(_i(63, 29, 16, 0x10))   # sd s0,16(sp)
    m.emit(_i(63, 29, 17, 0x18))   # sd s1,24(sp)
    m.emit(_r(4, 0, 16, 0, 37))    # move s0,a0; text object handle
    m.emit(_r(5, 0, 17, 0, 37))    # move s1,a1; item-name source pointer
    m.emit(_jal(ORIGINAL_TEXT_SETTER))
    m.emit(0)
    m.const(8, name_ptr)          # t0 = exact approved item name pointer
    m.branch(5, 17, 8, "done")    # other item/name => untouched
    m.emit(0)
    m.branch(4, 16, 0, "done")    # guard a null text handle
    m.emit(0)
    m.emit(_r(16, 0, 4, 0, 37))   # move a0,s0; target text object
    m.const(8, _float_word(FIT_HORIZONTAL_SCALE))
    m.emit((17 << 26) | (4 << 21) | (8 << 16) | (12 << 11))  # mtc1 t0,f12
    m.const(8, _float_word(1.0))
    m.emit((17 << 26) | (4 << 21) | (8 << 16) | (13 << 11))  # mtc1 t0,f13
    m.emit(_jal(NATIVE_XY_SCALING_SETTER))
    m.emit(0)
    m.label("done")
    m.emit(_i(55, 29, 17, 0x18))   # ld s1,24(sp)
    m.emit(_i(55, 29, 16, 0x10))   # ld s0,16(sp)
    m.emit(_i(55, 29, 31, 0x20))   # ld ra,32(sp)
    m.emit(_i(9, 29, 29, 0x30))
    m.emit(_r(31, 0, 0, 0, 8))    # jr ra
    m.emit(0)
    return m.done()


def apply(source: bytes) -> tuple[bytes, dict]:
    if sha(source) != APPROVED_ELF_SHA256:
        raise ValueError("Not the exact gameplay-approved r67.14q ELF")
    typ, fo, va, _, size, reserve, flags, align = struct.unpack_from("<8I", source, 0x54)
    if (typ, fo, va, fo + size, reserve, flags, align) != (
        1, ELF_SEGMENT_FO, ELF_SEGMENT_VA, len(source), ELF_SEGMENT_RESERVE, 7, 16
    ):
        raise ValueError("Unexpected PS2 translation PT_LOAD layout")
    pointer = item_pointer(source)
    for site, words in CALL_CONTEXTS.items():
        off = site - ELF_BIAS - 8
        if struct.unpack_from("<4I", source, off) != words:
            raise ValueError(f"Unrecognized native name-text owner at {site:#x}")
    changed = bytearray(source)
    while len(changed) & 3:
        changed.append(0)
    helper_va = va + len(changed) - fo
    helper = make_helper(pointer)
    if helper_va & 3 or len(changed) + len(helper) - fo > reserve:
        raise ValueError("Private helper alignment or ELF reservation error")
    changed.extend(helper)
    for site in CALL_SITES:
        struct.pack_into("<I", changed, site - ELF_BIAS, _jal(helper_va))
    struct.pack_into("<I", changed, 0x64, len(changed) - fo)
    allowed = set(range(0x64, 0x68))
    for site in CALL_SITES:
        allowed.update(range(site - ELF_BIAS, site - ELF_BIAS + 4))
    modified = [i for i, (old, new) in enumerate(zip(source, changed)) if old != new]
    if not modified or set(modified) - allowed:
        raise ValueError(f"Unexpected changes outside item-label owners: {set(modified) - allowed}")
    for required in (b"SLPM-66511", b"BISLPM-66511Save"):
        if required not in changed:
            raise ValueError("Original game/save identity missing")
    result = bytes(changed)
    return result, {
        "release": "r67.14r",
        "status": "DIAGNOSTIC_ONLY_AWAITING_VISUAL_ACCEPTANCE",
        "approved_source_sha256": APPROVED_ELF_SHA256,
        "candidate_elf_sha256": sha(result),
        "old_elf_size": len(source),
        "new_elf_size": len(result),
        "lion_item_id": ITEM_ID,
        "lion_string_pointer": hex(pointer),
        "horizontal_scale": FIT_HORIZONTAL_SCALE,
        "vertical_scale": 1.0,
        "private_helper_va": hex(helper_va),
        "private_helper_size": len(helper),
        "call_sites": [hex(site) for site in CALL_SITES],
        "modified_source_offsets": [hex(i) for i in modified],
        "appended_bytes": len(result) - len(source),
        "other_items_unchanged_by_pointer_gate": True,
        "original_item_catalog_unchanged": True,
        "save_data_modified": False,
        "runtime_verified": False,
        "release_approved": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("input", "output", "report"):
        parser.add_argument("--" + arg, required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("Never overwrite a previous candidate/report")
    result, report = apply(args.input.read_bytes())
    args.output.write_bytes(result)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
