"""r67.14k diagnostic: generic companion EVENT dialogue fit, not string-specific.

User rejected r67.14j's post-render glyph-node edits: wrong Y placement
and missing text. Start from visually near-correct r67.14i, where t0/native
renderer args are fixed, and change only the native event-comment policy:
- Both H_TalkBuddyTask <0x259 comment-render callsites are used by every
  companion event, not just the three Chamber strings.
- Their two existing private wrappers enter the SAME matched layout path for
  any non-null event text, preserving the proven per-row Y=280/300, X origins,
  t0/t1 argument restoration, width of actual glyph (0.40), bubble and timing.
- Its existing pre-layout font hook keeps guarding against other UIs via
  s7=LION, but changes only the FONT X advance scale 0.55 to 0.44. Native
  glyph builder reads +0x48 at 0x18D008/0x18DA9C, BEFORE positioning nodes.
- 0.44 * 16*38 = 267.52 native units: fits the 288-unit bubble with padding.
  No text strings are shortened; no glyph nodes are mutated after creation.
- AFK/free-talk records >=0x259 use the OTHER specialized constructor
  0x1950A0 and already have native record-driven wrapping for all 30
  companions. Preserve their own generic path; do not cross-patch it.

This is a DIAGNOSTIC ISO requiring fresh user visual confirmation.
"""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path

from tools.r67_chamber_pre_glyph_font_target import sha
from tools.r67_chamber_story_text_only import (
    _i, _float_word, ELF_SEGMENT_VA, ELF_SEGMENT_FO
)

SOURCE_SHA256="3f11b7ff426a8249b908d98b89ad194a2bbef9593297b2adb95003424e39abe8"
WRAPPER_UNMATCHED_BRANCH_VAS=(0x963D68,0x963E44)
PRE_LAYOUT_FACTOR_HI_VA=0x963CFC
PRE_LAYOUT_FACTOR_LO_VA=0x963D00
PREVIOUS_FONT_ADVANCE=0.55
GENERIC_FONT_ADVANCE=0.44
MAX_EVENT_CHARS=38
NATIVE_GLYPH_ADVANCE=16
BUBBLE_WIDTH=288
PADDING_EACH_SIDE=10
# Prior wrapper b render; both changed to b matched with no delay-slot mutation
BRANCH_TO_MATCHED=_i(4,0,0,1)
OLD_EVENT_COUNT_BOUNDARY=0x259

def apply(source:bytes)->tuple[bytes,dict]:
    if sha(source)!=SOURCE_SHA256:
        raise ValueError("Source is not verified r67.14i: refusing accidental j/k reapplication")
    original=bytes(source)
    data=bytearray(source)
    branch_deltas=[]
    for address in WRAPPER_UNMATCHED_BRANCH_VAS:
        fileoff=ELF_SEGMENT_FO+address-ELF_SEGMENT_VA
        old=struct.unpack_from('<I',data,fileoff)[0]
        if old not in (_i(4,0,0,15),_i(4,0,0,15)):
            raise ValueError(f"Unexpected unmatched-branch preimage: {address:#x} {old:#x}")
        if struct.unpack_from('<I',data,fileoff+4)[0]!=0:
            raise ValueError(f"Branch delay-slot is not NOP: {address:#x}")
        struct.pack_into('<I',data,fileoff,BRANCH_TO_MATCHED)
        branch_deltas.append((hex(address),hex(old),hex(BRANCH_TO_MATCHED)))
    old_word=_float_word(PREVIOUS_FONT_ADVANCE)
    new_word=_float_word(GENERIC_FONT_ADVANCE)
    hi=_i(15,0,9,old_word>>16)
    lo=_i(13,9,9,old_word&0xffff)
    for addr,expected,changed in (
        (PRE_LAYOUT_FACTOR_HI_VA,hi,_i(15,0,9,new_word>>16)),
        (PRE_LAYOUT_FACTOR_LO_VA,lo,_i(13,9,9,new_word&0xffff)),
    ):
        off=ELF_SEGMENT_FO+addr-ELF_SEGMENT_VA
        prior=struct.unpack_from('<I',data,off)[0]
        if prior != expected:
            raise ValueError(f"Original scale word drifted at {addr:#x}: {prior:#x}")
        struct.pack_into('<I',data,off,changed)
    mutation_offsets=[i for i,(a,b) in enumerate(zip(original,data)) if a!=b]
    allowed={
        ELF_SEGMENT_FO+addr-ELF_SEGMENT_VA+offset
        for addr in (*WRAPPER_UNMATCHED_BRANCH_VAS,PRE_LAYOUT_FACTOR_HI_VA,PRE_LAYOUT_FACTOR_LO_VA)
        for offset in range(4)
    }
    if not mutation_offsets or set(mutation_offsets)-allowed or len(data)!=len(original):
        raise ValueError("Unexpected original ELF edits")
    # Validate all event English corpus lengths without changing any words.
    from tools.companion_hud_data import COMPANION_COMMENT_DATA
    from tools.companion_afk_data import COMPANION_AFK_TRANSLATIONS
    if len(COMPANION_COMMENT_DATA)!=1650 or len(COMPANION_AFK_TRANSLATIONS)!=600:
        raise ValueError("Companion event/AFK corpus cardinality drift")
    lengths=[len(row[2]) for row in COMPANION_COMMENT_DATA]
    if min(lengths)<1 or max(lengths)>MAX_EVENT_CHARS:
        raise ValueError(f"Unbounded event text length: max={max(lengths)}")
    if MAX_EVENT_CHARS*NATIVE_GLYPH_ADVANCE*GENERIC_FONT_ADVANCE>=BUBBLE_WIDTH-2*PADDING_EACH_SIDE:
        raise ValueError("Worst-case comment cannot fit green body")
    return bytes(data),dict(
        revision="r67.14k",
        status="DIAGNOSTIC_UNVERIFIED_VISUALLY",
        source_sha256=sha(original),
        staged_sha256=sha(data),
        changed_existing_bytes=len(mutation_offsets),
        changed_byte_offsets=[hex(i) for i in mutation_offsets],
        event_wrapper_unmatched_branches=branch_deltas,
        generically_handled_original_event_record_count=OLD_EVENT_COUNT_BOUNDARY,
        companion_event_english_lines=len(COMPANION_COMMENT_DATA),
        event_max_chars=max(lengths),
        event_policy="both original H_TalkBuddyTask event render callsites, no literal string pointer eligibility",
        event_native_advance_factor=GENERIC_FONT_ADVANCE,
        event_max_estimated_advance=MAX_EVENT_CHARS*NATIVE_GLYPH_ADVANCE*GENERIC_FONT_ADVANCE,
        afk_existing_generic_wrap_records=len(COMPANION_AFK_TRANSLATIONS),
        afk_native_constructor_va="0x1950a0",
        afk_layout_unchanged=True,
        post_layout_glyph_node_mutation=False,
        approved_row_y_font_width_bubble_backing_timing_history_and_hant_unchanged=True,
        runtime_verified=False,
        release_approved=False
    )

def main()->None:
    a=argparse.ArgumentParser(description=__doc__)
    for flag in ("input","output","report"):a.add_argument('--'+flag,required=True,type=Path)
    args=a.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("Refusing to overwrite existing diagnostic files")
    artifact,report=apply(args.input.read_bytes())
    args.output.write_bytes(artifact)
    args.report.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
