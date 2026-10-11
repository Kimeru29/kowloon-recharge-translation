"""r67.14q: fit the sole overflowing opening SECOND dialogue row with wording only.

r67.14p user screenshots confirm Eerie, first opening row, all other companion
event messages, timing, green/blue bubble and AFK are now correct. The second
opening row's last word 'time.' crosses the right border, despite horizontal
advance already matching glyph width at 0.40. Further horizontal compression
would overlap neighboring glyphs; changing global code would risk all events.

Only reword this source field:
  'switch into battle mode at any time.' (36 cells)
  'switch into battle mode anytime.'     (32 cells)
Semantic meaning preserved (NOT a verbatim official PS4 English line). Same
cell count as already accepted first opening row (32). Native glyph width,
spacing, vertical origin, two-line bubble, four-second event hold and all AFK
remain byte-for-byte unchanged.

NO record headers/control-flow/timers or any other strings modified.
Diagnostic: must be visually approved by user after cold boot.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from tools.r67_chamber_pre_glyph_font_target import sha
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO,ELF_SEGMENT_VA,ELF_SEGMENT_RESERVE
from tools.r67_companion_event_complete_opening_only import (
    FIRST_ALIAS,SECOND_ALIAS,THIRD_HEADER,THIRD_POINTER,
    EERIE_HEADER,EERIE_POINTER,DOOR_FIRST,DOOR_SECOND,REFLOW
)
from tools.r67_companion_event_final_spacing_timing import NEW_EVENT_ADVANCE,NEW_EVENT_TIMER
from tools.localization import encode_ps2_english

SOURCE_SHA256="8d1266d1a318839aec8090a89f8f05629251e6a61e736cd62d2856aea1e8526b"
ORIGINAL_LONG_LINE="switch into battle mode at any time."
FIT_LINE="switch into battle mode anytime."
FIRST_LINE="Make sure you're always ready to"
EXPECTED_FROZEN={
    FIRST_ALIAS:0x963F00,
    SECOND_ALIAS:0x963F42,
    THIRD_HEADER:1,
    THIRD_POINTER:0x92D140,
    EERIE_HEADER:1,
    EERIE_POINTER:0x9630BA,
    DOOR_FIRST:0x962DC8,
    DOOR_SECOND:0x92D854,
}

def apply(source:bytes)->tuple[bytes,dict]:
    if sha(source)!=SOURCE_SHA256:
        raise ValueError("Wrong r67.14p baseline (no reapplication or unknown ELF)")
    if (len(ORIGINAL_LONG_LINE),len(FIT_LINE),len(FIRST_LINE))!=(36,32,32):
        raise ValueError("Expected native text cell length changed")
    # Require a narrowly equivalent English rewording; never drop the
    # essential 'switch into battle mode' or the temporal qualification.
    if not (FIT_LINE.startswith("switch into battle mode ") and FIT_LINE.endswith("anytime.")):
        raise ValueError("Narrow semantic wording guard failed")
    if NEW_EVENT_ADVANCE!=0.4 or NEW_EVENT_TIMER!=240:
        raise ValueError("Approved r67.14p font/timer policy drift")
    data=bytearray(source)
    typ,fo,va,paddr,size,reserve,flags,align=struct.unpack_from("<8I",data,0x54)
    if (typ,fo,va,fo+size,reserve,flags,align)!=(
        1,ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(source),ELF_SEGMENT_RESERVE,7,16
    ):
        raise ValueError("Unexpected ELF executable segment preimage")
    for off,expected in EXPECTED_FROZEN.items():
        actual=struct.unpack_from("<I",source,off)[0]
        if actual!=expected:raise ValueError(f"Expected source alias/header drift at {off:#x}: {actual:#x}")
    def encoded_at(pointer:int, phrase:str)->bool:
        pos=fo+pointer-va
        expected=encode_ps2_english(phrase,collapse_spaces=False)+b"\x00"
        return data[pos:pos+len(expected)]==expected
    if not encoded_at(EXPECTED_FROZEN[FIRST_ALIAS],FIRST_LINE):
        raise ValueError("Previously approved first opening row changed")
    if not encoded_at(EXPECTED_FROZEN[SECOND_ALIAS],ORIGINAL_LONG_LINE):
        raise ValueError("Expected long second row missing in source")
    if len(data)&1:data.append(0)
    newptr=va+len(data)-fo
    textbytes=encode_ps2_english(FIT_LINE,collapse_spaces=False)+b"\x00"
    data.extend(textbytes)
    if len(data)-fo>reserve:
        raise ValueError("No room left in reserved ELF segment")
    struct.pack_into("<I",data,SECOND_ALIAS,newptr)
    struct.pack_into("<I",data,0x64,len(data)-fo)
    changed={i for i,(a,b) in enumerate(zip(source,data)) if a!=b}
    allowed=set(range(SECOND_ALIAS,SECOND_ALIAS+4))|set(range(0x64,0x68))
    if not changed or changed-allowed:
        raise ValueError(f"Unexpected change to original executable outside exact second pointer: {changed-allowed}")
    for off,word in EXPECTED_FROZEN.items():
        expected=newptr if off==SECOND_ALIAS else word
        if struct.unpack_from("<I",data,off)[0]!=expected:
            raise ValueError(f"Frozen native event control modified at {off:#x}")
    return bytes(data),{
        "revision":"r67.14q","status":"DIAGNOSTIC_AWAITING_VISUAL_ACCEPTANCE",
        "original_r67_14p_sha256":sha(source),"candidate_elf_sha256":sha(data),
        "original_official_line":ORIGINAL_LONG_LINE,
        "shortened_semantically_equivalent_line":FIT_LINE,
        "official_source_text_verbatim":False,
        "old_cells":len(ORIGINAL_LONG_LINE),"new_cells":len(FIT_LINE),
        "first_row_cells":len(FIRST_LINE),
        "patched_alias":hex(SECOND_ALIAS),
        "old_pointer":hex(EXPECTED_FROZEN[SECOND_ALIAS]),
        "new_pointer":hex(newptr),
        "new_text_bytes":len(textbytes),
        "modified_original_byte_count":len(changed),
        "modified_original_offsets":[hex(i) for i in sorted(changed)],
        "all_native_renderers_glyphs_bubble_geometry_timer_afk_history_unmodified":True,
        "runtime_verified":False,"release_approved":False
    }

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("input","output","report"):parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("Refuse to overwrite previous candidate")
    result,report=apply(args.input.read_bytes())
    args.output.write_bytes(result)
    args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__": main()
