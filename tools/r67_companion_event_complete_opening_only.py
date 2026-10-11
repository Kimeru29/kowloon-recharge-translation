"""r67.14o: Complete the opening automatic-event sentence, text pointers ONLY.

r67.14n was rejected because zeroing its third native event record header
regressed 'Eerie place.' into text above an empty bubble. Therefore DO NOT
alter ANY native event record/header, visibility rule, timing, or code here.

r67.14m is the visually accepted baseline: two lines fit the correct bubble,
but the complete official transcript's final 'any time.' fails to appear as
a later event. Reflow the exact official words into the original TWO fields of
that same working bubble. Unlike rejected r67.14n, do not modify the third
record, source pointer, or the separate door caption. No AFK/freetalk edits.

DIAGNOSTIC: user must cold-boot and verify. Third event remains intact to
preserve all native scheduling; if game also displays it, investigate without
hiding the record by modifying its header.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from tools.localization import encode_ps2_english
from tools.companion_hud_data import COMPANION_COMMENT_DATA
from tools.r67_chamber_pre_glyph_font_target import sha
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO, ELF_SEGMENT_VA, ELF_SEGMENT_RESERVE

BASE_SHA = "ea5e9bedb668c23f8e43e71ee22b391cb37c9e9eb989894cb1482c1341502ca1"
FIRST_ALIAS, SECOND_ALIAS = 0x3D3438, 0x3D343C
THIRD_HEADER, THIRD_POINTER = 0x3D3440, 0x3D3448
EERIE_HEADER, EERIE_POINTER = 0x3D3420, 0x3D3428
DOOR_FIRST, DOOR_SECOND = 0x3D3B28, 0x3D3B2C
ORIGINAL_POINTERS = (0x92D0C8, 0x92D104)
ORIGINAL_FIRST = "Make sure you're always ready"
ORIGINAL_SECOND = "to switch into battle mode at"
ORIGINAL_THIRD = "any time."
REFLOW = ("Make sure you're always ready to", "switch into battle mode at any time.")
MAX_CHARS = 38


def apply(source: bytes) -> tuple[bytes, dict]:
    if sha(source) != BASE_SHA:
        raise ValueError("Wrong r67.14m source ELF or attempted reapplication")
    source_words = {r[0]: r[2] for r in COMPANION_COMMENT_DATA}
    if (source_words[0x3C1A70], source_words[0x3C1A88], source_words[0x3C1AA0]) != (
        ORIGINAL_FIRST, ORIGINAL_SECOND, ORIGINAL_THIRD
    ):
        raise ValueError("Official original transcript differs")
    original_sentence = " ".join((ORIGINAL_FIRST, ORIGINAL_SECOND, ORIGINAL_THIRD))
    if original_sentence != " ".join(REFLOW):
        raise ValueError("Incorrect text: exact official transcript not preserved")
    from tools.r67_companion_event_generic_fit import GENERIC_FONT_ADVANCE,NATIVE_GLYPH_ADVANCE,BUBBLE_WIDTH,PADDING_EACH_SIDE
    if any(len(x)>MAX_CHARS or len(x)*GENERIC_FONT_ADVANCE*NATIVE_GLYPH_ADVANCE>=BUBBLE_WIDTH-2*PADDING_EACH_SIDE for x in REFLOW):
        raise ValueError("New text would exceed the approved native bubble content")
    original=bytes(source); output=bytearray(source)
    typ,fo,va,paddr,size,reserve,flags,align=struct.unpack_from("<8I",output,0x54)
    if (typ,fo,va,fo+size,reserve,flags,align)!=(1,ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(source),ELF_SEGMENT_RESERVE,7,16):
        raise ValueError("Private executable segment layout drifted")
    expected={
        FIRST_ALIAS:ORIGINAL_POINTERS[0],
        SECOND_ALIAS:ORIGINAL_POINTERS[1],
        THIRD_HEADER:1,
        THIRD_POINTER:0x92D140,
        EERIE_HEADER:1,
        EERIE_POINTER:0x9630BA,
        DOOR_FIRST:0x962DC8,
        DOOR_SECOND:0x92D854,
    }
    for off,value in expected.items():
        actual=struct.unpack_from("<I",original,off)[0]
        if actual!=value:
            raise ValueError(f"Frozen native event record or text pointer drift {off:#x}: {actual:#x} != {value:#x}")
    changes={}
    for offset,text in ((FIRST_ALIAS,REFLOW[0]),(SECOND_ALIAS,REFLOW[1])):
        if len(output)%2:output.append(0)
        new_ptr=va+len(output)-fo
        output.extend(encode_ps2_english(text,collapse_spaces=False)+b"\x00")
        struct.pack_into("<I",output,offset,new_ptr)
        changes[hex(offset)]={"previous":hex(expected[offset]),"new":hex(new_ptr),"official_text":text}
    if len(output)-fo>reserve:
        raise ValueError("Reserved ELF executable space exceeded")
    struct.pack_into("<I",output,0x64,len(output)-fo)
    before_changes=[i for i,(a,b) in enumerate(zip(original,output)) if a!=b]
    allowed=set(range(0x64,0x68)) | set(range(FIRST_ALIAS,FIRST_ALIAS+4)) | set(range(SECOND_ALIAS,SECOND_ALIAS+4))
    if not before_changes or set(before_changes)-allowed:
        raise ValueError("Unapproved modification outside precisely two text pointer slots and ELF size")
    for off in (THIRD_HEADER,THIRD_POINTER,EERIE_HEADER,EERIE_POINTER,DOOR_FIRST,DOOR_SECOND):
        if struct.unpack_from("<I",output,off)[0]!=expected[off]:
            raise ValueError(f"Locked event record changed at {off:#x}")
    return bytes(output),dict(
        revision="r67.14o",status="DIAGNOSTIC_GAMEPLAY_APPROVAL_REQUIRED",
        source_sha256=sha(source),output_sha256=sha(output),
        official_original_sentence=original_sentence,
        joined_visible_text=" ".join(REFLOW),
        modified_only_two_existing_pointer_aliases=changes,
        native_third_record_header_untouched=True,
        native_third_record_pointer_untouched=True,
        original_eerie_place_record_untouched=True,
        original_door_dialogue_untouched=True,
        native_renderer_blue_bubble_afk_timers_histories_unchanged=True,
        source_bytes_changed=len(before_changes),
        source_offsets_changed=[hex(i) for i in before_changes],
        runtime_verified=False,release_approved=False,
    )

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    for option in ("input","output","report"):p.add_argument("--"+option,required=True,type=Path)
    args=p.parse_args()
    if args.output.exists() or args.report.exists():raise FileExistsError("Refusing to overwrite prior candidate")
    artifact,metadata=apply(args.input.read_bytes())
    args.output.write_bytes(artifact)
    args.report.write_text(json.dumps(metadata,sort_keys=True,indent=2)+"\n")
    print(json.dumps(metadata,sort_keys=True))

if __name__=="__main__":main()
