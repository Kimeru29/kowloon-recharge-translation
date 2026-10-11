"""r67.14i: Restore native renderer's t0 text argument in JAL delay slots.

A real r67.14g in-game slot-1 snapshot proved the active speech script's
first pointer was "Eerie place." (0x9630BA) while native glyph nodes rendered
"any time." (last compare constant 0x92D140). The r67.14g match guard uses
t0 to compare pointers and never restores the caller's original t0 before
calling native 0x189E40, whose prologue explicitly saves t0 (0x189E68).
This fixes exactly two private-comment-helper JAL delay-slot NOPs,
replacing each with lw t0,4(sp). No branches, text data, globals, native
code, visual backing, times, pre-font layout logic or save identities change.

DIAGNOSTIC ONLY until a real cold-boot screenshot confirms text fit.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from tools.r67_chamber_pre_glyph_font_target import sha
from tools.r67_chamber_story_text_only import (
    _jal, _i, ORIGINAL_RENDERER_VA, ELF_SEGMENT_FO, ELF_SEGMENT_VA,
    ELF_BIAS,
)

APPROVED_G_SHA256 = "e966703fdb54719063f71059c7d8d513dd85e5e292435c2fbaacb5e72526d72c"
G_WRAPPERS = ((0x1661BC, 0x963D20), (0x16628C, 0x963DFC))
JAL_BYTE_OFFSET = 140
DELAY_SLOT_ORIGINAL = 0
RESTORE_T0_FROM_STACK = _i(35, 29, 8, 4)  # lw t0,4(sp), saved at helper entry
RESTORE_T1_FROM_STACK = _i(35, 29, 9, 8)  # prior lw t1,8(sp)

def patch(source: bytes) -> tuple[bytes, dict]:
    if sha(source) != APPROVED_G_SHA256:
        raise ValueError("r67.14g staged ELF SHA-256 drift: refusing wrong binary")
    output = bytearray(source)
    changes = []
    expected_jal = _jal(ORIGINAL_RENDERER_VA)
    for source_site, helper_va in G_WRAPPERS:
        target = struct.unpack_from("<I", source, source_site-ELF_BIAS)[0]
        if target != _jal(helper_va):
            raise ValueError(f"Original story hook drift: {source_site:#x}")
        helper_fo = ELF_SEGMENT_FO + helper_va - ELF_SEGMENT_VA
        call_fo = helper_fo + JAL_BYTE_OFFSET
        before = struct.unpack_from("<3I", source, call_fo-4)
        if before != (RESTORE_T1_FROM_STACK, expected_jal, DELAY_SLOT_ORIGINAL):
            raise ValueError(f"Native call preimage drift: {helper_va:#x} {before}")
        # jal 0x189E40; lw t0,4(sp) (MIPS branch delay slot).
        # The original renderer does not use t0 until its later prologue.
        struct.pack_into("<I", output, call_fo+4, RESTORE_T0_FROM_STACK)
        changes.append({
            "story_callsite": hex(source_site),
            "wrapper_va": hex(helper_va),
            "native_renderer_call_va": hex(helper_va+JAL_BYTE_OFFSET),
            "modified_delay_va": hex(helper_va+JAL_BYTE_OFFSET+4),
            "original": hex(DELAY_SLOT_ORIGINAL),
            "new": hex(RESTORE_T0_FROM_STACK),
        })
    changed = [i for i,(a,b) in enumerate(zip(source,output)) if a!=b]
    allow = {
        ELF_SEGMENT_FO + helper - ELF_SEGMENT_VA + JAL_BYTE_OFFSET + 4 + offset
        for _,helper in G_WRAPPERS for offset in range(4)
        }
    if not changed or set(changed) - allow or len(changed) != 6:
        raise ValueError(f"Unexpected patch differences: {set(changed)-allow}, count={len(changed)}")
    if len(output)!=len(source):
        raise ValueError("Native ELF size changed")
    return bytes(output), {
        "revision": "r67.14i",
        "status": "DIAGNOSTIC_NOT_VISUALLY_ACCEPTED",
        "source_sha256": sha(source),
        "patched_sha256": sha(output),
        "changed_existing_bytes": len(changed),
        "changed_words": changes,
        "original_renderer_unmodified": True,
        "font_scale_and_y_unchanged_from_r67_14g": True,
        "backing_timing_script_hant_and_history_untouched": True,
        "runtime_verified": False,
        "release_approved": False,
    }

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ("input","output","report"):
        p.add_argument("--"+flag,required=True,type=Path)
    args=p.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("Refusing overwrite of previous diagnostic artifacts")
    staged,report=patch(args.input.read_bytes())
    args.output.write_bytes(staged)
    args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__": main()
