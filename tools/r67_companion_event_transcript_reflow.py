"""r67.14n: preserve the complete official Chamber comment inside one 2-line event.

The generic event renderer/timing and fully working AFK are unchanged.
User r67.14m screenshots show 2 successful lines ending "...battle mode at",
followed by the event terminating before the existing third ("any time.").
The native record table has three successive 16-byte rows; the first is a
true simultaneous two-field bubble and the third is a separate bubble.
Reflow the THREE original official fragments, without omission, into the
TWO native fields of the known original event bubble; terminate after those
fields so there is no duplicate/empty third event. All other 600 original
event records and all AFK/free-talk remain byte-identical.

A separate ancient r67.02 workaround shortened "Good. The door should be"
to "Door's ready." while the bubble overflowed; now native generic 0.44
advance can show the exact official first half next to "unlocked now.".
Restore that *existing official PS4 English wording*, no guess/translation.

No renderer code, AFK state, dimensions, blue backing, glyph Y/X, timing,
H.A.N.T., history or user saves are changed. Visual user acceptance required.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from tools.localization import encode_ps2_english
from tools.r67_chamber_pre_glyph_font_target import sha
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO,ELF_SEGMENT_VA,ELF_SEGMENT_RESERVE
from tools.companion_hud_data import COMPANION_COMMENT_DATA

SOURCE_SHA256="ea5e9bedb668c23f8e43e71ee22b391cb37c9e9eb989894cb1482c1341502ca1"
FIRST_FIELD_PTR=0x3D3438
SECOND_FIELD_PTR=0x3D343C
THIRD_RECORD_HEADER=0x3D3440
THIRD_RECORD_TEXT_PTR=0x3D3448
DOOR_FIRST_FIELD_PTR=0x3D3B28
DOOR_SECOND_FIELD_PTR=0x3D3B2C

EXPECTED={
    FIRST_FIELD_PTR:0x92D0C8,
    SECOND_FIELD_PTR:0x92D104,
    THIRD_RECORD_HEADER:0x00000001,
    THIRD_RECORD_TEXT_PTR:0x92D140,
    DOOR_FIRST_FIELD_PTR:0x962DC8,
    DOOR_SECOND_FIELD_PTR:0x92D854
}
# Two lines, each <= native 38-char limit; concatenation is exact PS4 script.
FIRST_TEXT="Make sure you're always ready to"
SECOND_TEXT="switch into battle mode at any time."
OFFICIAL_DOOR="Good. The door should be"
LINE_LIMIT=38

def reflow(original:bytes)->tuple[bytes,dict]:
    if sha(original)!=SOURCE_SHA256:
        raise ValueError("Wrong r67.14m source ELF or attempted reapplication")
    from tools.r67_companion_event_generic_fit import GENERIC_FONT_ADVANCE,NATIVE_GLYPH_ADVANCE,BUBBLE_WIDTH,PADDING_EACH_SIDE
    from tools.r67_companion_event_stable_timing import EVENT_DURATION_FRAMES
    if EVENT_DURATION_FRAMES!=300 or GENERIC_FONT_ADVANCE!=0.44:
        raise ValueError("Accepted companion event renderer or timer policy drifted")
    sources={v[0]:v[2] for v in COMPANION_COMMENT_DATA}
    original_fragment_sources=(0x3C1A70,0x3C1A88,0x3C1AA0)
    official_fragments=tuple(sources[k] for k in original_fragment_sources)
    if official_fragments!=(
        "Make sure you're always ready","to switch into battle mode at","any time."
    ):
        raise ValueError("Official three-part Chamber transcript drifted")
    if " ".join(official_fragments)!=" ".join((FIRST_TEXT,SECOND_TEXT)):
        raise ValueError("Reflow omits or alters PS4 official wording")
    if sources[0x3C1F38]!=OFFICIAL_DOOR or sources[0x3C1F50]!="unlocked now.":
        raise ValueError("Original official paired door message drifted")
    for t in (FIRST_TEXT,SECOND_TEXT,OFFICIAL_DOOR):
        if len(t)>LINE_LIMIT or len(t)*NATIVE_GLYPH_ADVANCE*GENERIC_FONT_ADVANCE>=BUBBLE_WIDTH-2*PADDING_EACH_SIDE:
            raise ValueError(f"Reflow line does not fit approved native bubble: {t}")
    base=bytearray(original)
    typ,fo,va,paddr,size,reserve,flags,align=struct.unpack_from("<8I",base,0x54)
    if (typ,fo,va,fo+size,reserve,flags,align)!=(
        1,ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(base),ELF_SEGMENT_RESERVE,7,16
    ):
        raise ValueError("Unexpected translation PT_LOAD segment layout")
    for off,expected in EXPECTED.items():
        if struct.unpack_from("<I",base,off)[0]!=expected:
            raise ValueError(f"Original event pointer/table drift at {off:#x}")
    def append(text:str)->int:
        if len(base)&1:base.append(0)
        pointer=va+len(base)-fo
        base.extend(encode_ps2_english(text,collapse_spaces=False)+b"\x00")
        return pointer
    patched_fields={}
    for field,text in (
        (FIRST_FIELD_PTR,FIRST_TEXT),
        (SECOND_FIELD_PTR,SECOND_TEXT),
        (DOOR_FIRST_FIELD_PTR,OFFICIAL_DOOR)
    ):
        newptr=append(text)
        struct.pack_into("<I",base,field,newptr)
        patched_fields[hex(field)]=dict(previous=hex(EXPECTED[field]),new_pointer=hex(newptr),text=text)
    # The complete first sentence is now inside the two existing fields.
    # Mark the now redundant third event row absent so it cannot show empty
    # bubbles or repeat "any time." (keep its original string pointer intact).
    struct.pack_into("<I",base,THIRD_RECORD_HEADER,0)
    if len(base)-fo>reserve:
        raise ValueError("Insufficient reserved executable space")
    struct.pack_into("<I",base,0x64,len(base)-fo)
    original_differences={i for i,(a,b) in enumerate(zip(original,base)) if a!=b}
    allow=set(range(0x64,0x68))
    for addr in (*patched_fields.keys(),):
        at=int(addr,16);allow.update(range(at,at+4))
    allow.update(range(THIRD_RECORD_HEADER,THIRD_RECORD_HEADER+4))
    if not original_differences or original_differences-allow:
        raise ValueError("Original binary unexpectedly changed outside allowed text pointers and record header")
    return bytes(base),dict(
        revision="r67.14n",status="DIAGNOSTIC_VISUAL_APPROVAL_REQUIRED",
        source_14m_sha256=sha(original),output_elf_sha256=sha(base),
        original_official_sentence=" ".join(official_fragments),
        displayed_reflowed_sentence=" ".join((FIRST_TEXT,SECOND_TEXT)),
        two_native_fields=patched_fields,
        third_record_header_previous=1,third_record_header_new=0,
        third_string_pointer_unchanged=hex(EXPECTED[THIRD_RECORD_TEXT_PTR]),
        event_lines_max_width=LINE_LIMIT,
        preserved_event_300_frame_hold=True,
        unchanged_afk_free_talk_30_companions=True,
        original_executable_modified_positions=[hex(i) for i in sorted(original_differences)],
        source_lengths=[len(FIRST_TEXT),len(SECOND_TEXT),len(OFFICIAL_DOOR)],
        first_door_field_restored_official=True,
        runtime_approved=False,release_approved=False,
    )

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("input","output","report"):p.add_argument("--"+arg,required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():
        raise FileExistsError("Refuse to overwrite diagnostic artifacts")
    out,report=reflow(a.input.read_bytes())
    a.output.write_bytes(out)
    a.report.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
