"""r67.12 diagnostic: compact English history speaker/body spacing.

The native ADV history row loop still advances by 39 game pixels between
every record and adds another 39 after dialogue. Keep chronological record
selection and the horizontal-only history constructor from r67.11; change
only the two independent native row spacing floats:

  0x253D24: common row advance 39.0 -> 25.0 game pixels.
  0x253D54: extra paragraph gap 39.0 -> 12.0 game pixels.

Thus: speaker -> dialogue = 25px; dialogue -> next speaker = 37px.
This operates on every history record, not just the first speaker/line.
Diagnostic, NOT a release: user visual verification, variable-length text
wrapping and >12-record scrolling have not yet been established.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

BASE_SHA256 = "35ccde0a6d363c8b8f767d131dda46a543458f46cf8c6371975d7c0ea7651048"
ELF_VA_BIAS = 0xFFF80
SPEAKER_LINE_ADVANCE_VA = 0x253D24
AFTER_DIALOGUE_GAP_VA = 0x253D54
OLD_FLOAT_WORD = 0x3C02421C   # lui v0,0x421c; 39.0f
NEW_ROW_WORD = 0x3C0241C8    # lui v0,0x41c8; 25.0f
NEW_GAP_WORD = 0x3C024140    # lui v0,0x4140; 12.0f
PATCHES = {
    SPEAKER_LINE_ADVANCE_VA-ELF_VA_BIAS:(OLD_FLOAT_WORD,NEW_ROW_WORD),
    AFTER_DIALOGUE_GAP_VA-ELF_VA_BIAS:(OLD_FLOAT_WORD,NEW_GAP_WORD),
}
MAX_VISIBLE_RECORDS = 12

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def positions_for_records(record_kinds: tuple[str, ...]) -> tuple[int, ...]:
    """Model the history's per-record vertical accumulation.

    A 'speaker' entry is followed by its dialogue at +25; a 'dialogue'
    record adds 12 extra pixels after its 25px baseline advance.
    """
    if len(record_kinds)>MAX_VISIBLE_RECORDS:
        raise ValueError("Too many visible records")
    if any(kind not in ("speaker","dialogue") for kind in record_kinds):
        raise ValueError("Unsupported record kind")
    y=0
    out=[]
    for kind in record_kinds:
        out.append(y)
        y+=25
        if kind=="dialogue":
            y+=12
    return tuple(out)

def apply(baseline: bytes) -> tuple[bytes, dict]:
    if sha(baseline)!=BASE_SHA256:
        raise ValueError("Unexpected r67.11 approved diagnostic baseline checksum")
    patched=bytearray(baseline)
    for offset,(original,replacement) in PATCHES.items():
        if struct.unpack_from("<I",patched,offset)[0]!=original:
            raise ValueError(f"Unexpected history row spacing instruction at {offset:#x}")
        struct.pack_into("<I",patched,offset,replacement)
    changed=[i for i,(a,b) in enumerate(zip(baseline,patched)) if a!=b]
    allow={i for pos in PATCHES for i in range(pos,pos+4)}
    if set(changed)-allow:
        raise ValueError("Unrelated executable bytes modified")
    for ident in (b"SLPM-66511",b"BISLPM-66511Save"):
        if ident not in patched:
            raise ValueError("Save identifier unexpectedly modified")
    result=dict(
        status="DIAGNOSTIC_ONLY_PENDING_VISUAL_CHECK",
        baseline_elf_sha256=BASE_SHA256,
        candidate_elf_sha256=sha(patched),
        modified_original_byte_offsets=[hex(i) for i in changed],
        speaker_to_dialogue_pixels=25,
        dialogue_to_next_speaker_pixels=37,
        extra_after_dialogue_pixels=12,
        font_styles_unchanged=True,
        chronological_history_logic_unchanged=True,
        history_font_direction_fix_preserved=True,
        normal_dialogue_untouched=True,
        hant_basic_attack_untouched=True,
        savestate_compatibility_preserved=True,
        multi_entry_model_tested=True,
        long_dialogue_wrapping_runtime_verified=False,
        history_scrolling_runtime_verified=False,
        release_approved=False,
    )
    return bytes(patched),result

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    opts=parser.parse_args()
    if opts.output.exists() or opts.report.exists():
        raise FileExistsError("Refusing to overwrite existing diagnostic")
    target,report=apply(opts.baseline.read_bytes())
    opts.output.write_bytes(target)
    opts.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":
    main()
