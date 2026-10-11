"""r67.14p: targeted final EVENT horizontal advance and 20% lifetime adjustment.

From exact r67.14o ELF (the user's 6 screenshots confirm native bubble, text Y,
second-field rendering, 5-second events and AFK all working), change ONLY:

  - native pre-layout horizontal pen advance from .44 to .40, for the
    already-GUARDED automatic companion event renderer; glyph actual width
    stays .40, Y and text remain unchanged. No post-render glyph mutation.
  - event-only private timer helper's 300 frames to 240 frames (-20%).
    AFK record>=0x259 bypasses this timer store, and retains native AFK
    156/240 time overrides unchanged.

Never change any record/header, source string/pointer, AFK rendering, bubble
graphics, history, font-size/scale or animation. Strict baseline hash,
instruction preimages and mutation-byte whitelist are mandatory.
Not visually approved until user cold-boots the candidate.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from tools.r67_chamber_story_text_only import (
    ELF_SEGMENT_FO,ELF_SEGMENT_VA,ELF_BIAS,_i,_float_word
)
from tools.r67_chamber_pre_glyph_font_target import sha
from tools.r67_companion_event_generic_fit import (
    PRE_LAYOUT_FACTOR_HI_VA,PRE_LAYOUT_FACTOR_LO_VA,GENERIC_FONT_ADVANCE,
    NATIVE_GLYPH_ADVANCE,BUBBLE_WIDTH,PADDING_EACH_SIDE
)
from tools.r67_companion_event_stable_timing import (
    EVENT_DURATION_FRAMES,EVENT_BOUNDARY
)
from tools.r67_companion_event_complete_opening_only import (
    FIRST_ALIAS,SECOND_ALIAS,THIRD_HEADER,THIRD_POINTER,
    EERIE_HEADER,EERIE_POINTER,DOOR_FIRST,DOOR_SECOND,REFLOW
)
from tools.companion_afk_data import COMPANION_AFK_TRANSLATIONS
from tools.companion_hud_data import COMPANION_COMMENT_DATA

SOURCE_SHA256="e4ea77e146555da2c5c54e228bb86e5dda61cd7c4fc2708564694b21f899f759"
NEW_EVENT_ADVANCE=0.40
NEW_EVENT_TIMER=240
TIMER_IMMEDIATE_VA=0x963EF0
NATIVE_AFK_156_SET_VA=0x1662F8
NATIVE_AFK_240_SET_VA=0x166320
SCALE_WORDS=(PRE_LAYOUT_FACTOR_HI_VA,PRE_LAYOUT_FACTOR_LO_VA)

def apply(source:bytes)->tuple[bytes,dict]:
    if sha(source)!=SOURCE_SHA256:
        raise ValueError("Refusing unknown ELF: expected exact user-tested r67.14o")
    if GENERIC_FONT_ADVANCE!=0.44 or EVENT_DURATION_FRAMES!=300:
        raise ValueError("Base event layout/timing policy changed")
    if len(COMPANION_COMMENT_DATA)!=1650 or len(COMPANION_AFK_TRANSLATIONS)!=600:
        raise ValueError("Translated companion event/AFK corpus changed")
    if any(len(x)>38 for x in REFLOW):
        raise ValueError("Unexpected long opening text")
    if NEW_EVENT_ADVANCE*NATIVE_GLYPH_ADVANCE*max(map(len,REFLOW))>=BUBBLE_WIDTH-2*PADDING_EACH_SIDE:
        raise ValueError("New opening line still exceeds estimated content area")
    if NEW_EVENT_ADVANCE<0.40:
        raise ValueError("Do not let advance become narrower than approved 0.40 glyph width")
    if NEW_EVENT_TIMER*5!=EVENT_DURATION_FRAMES*4:
        raise ValueError("Event duration change is not exactly 20%")
    data=bytearray(source)
    def off(va:int)->int:return ELF_SEGMENT_FO+va-ELF_SEGMENT_VA
    old_bits=_float_word(GENERIC_FONT_ADVANCE)
    new_bits=_float_word(NEW_EVENT_ADVANCE)
    substitutions={
        PRE_LAYOUT_FACTOR_HI_VA:(_i(15,0,9,old_bits>>16),_i(15,0,9,new_bits>>16)),
        PRE_LAYOUT_FACTOR_LO_VA:(_i(13,9,9,old_bits&0xffff),_i(13,9,9,new_bits&0xffff)),
        TIMER_IMMEDIATE_VA:(_i(9,0,2,EVENT_DURATION_FRAMES),_i(9,0,2,NEW_EVENT_TIMER))
    }
    for site,(old,new) in substitutions.items():
        if struct.unpack_from("<I",source,off(site))[0]!=old:
            raise ValueError(f"Unexpected event-only instruction at {site:#x}")
        struct.pack_into("<I",data,off(site),new)
    # Precise hard locks: existing AFK 156 and 240-frame setters remain unchanged.
    for site,frames in ((NATIVE_AFK_156_SET_VA,156),(NATIVE_AFK_240_SET_VA,240)):
        expected=_i(9,0,2,frames)
        if struct.unpack_from("<I",source,site-ELF_BIAS)[0]!=expected:
            raise ValueError(f"Existing AFK duration instruction drifted at {site:#x}")
        if struct.unpack_from("<I",data,site-ELF_BIAS)[0]!=expected:
            raise ValueError("AFK timing instruction changed unexpectedly")
    # First two opening native text pointers remain exactly as tested.
    for site in (FIRST_ALIAS,SECOND_ALIAS,THIRD_HEADER,THIRD_POINTER,
                 EERIE_HEADER,EERIE_POINTER,DOOR_FIRST,DOOR_SECOND):
        if source[site:site+4]!=data[site:site+4]:
            raise ValueError(f"Frozen original event record or English text changed {site:#x}")
    changed={index for index,(a,b) in enumerate(zip(source,data)) if a!=b}
    allowed={off(site)+i for site in substitutions for i in range(4)}
    if not changed or changed-allowed or len(data)!=len(source):
        raise ValueError(f"Original ELF mutations outside exactly three event policy words: {sorted(changed-allowed)}")
    return bytes(data),{
        "revision":"r67.14p",
        "status":"DIAGNOSTIC_GAMEPLAY_REVIEW_REQUIRED",
        "source_14o_sha256":sha(source),"output_elf_sha256":sha(data),
        "previous_native_event_advance":GENERIC_FONT_ADVANCE,
        "new_native_event_advance":NEW_EVENT_ADVANCE,
        "preserved_native_event_glyph_width":0.40,
        "preserved_native_event_glyph_y_and_scale":True,
        "old_event_hold_frames":EVENT_DURATION_FRAMES,
        "new_event_hold_frames":NEW_EVENT_TIMER,
        "relative_event_duration_change":"-20%",
        "nominal_new_hold_seconds_at_60fps":NEW_EVENT_TIMER/60,
        "all_companion_event_comments_use_same_policy":True,
        "afk_156_and_240_timers_byte_identical":True,
        "afk_entire_code_and_free_talk_untouched":True,
        "all_translations_event_records_graphics_HANT_history_untouched":True,
        "changed_existing_byte_count":len(changed),
        "changed_positions":[hex(i) for i in sorted(changed)],
        "runtime_approved":False
    }

def main()->None:
    ap=argparse.ArgumentParser(description=__doc__)
    for a in ("input","output","report"):ap.add_argument("--"+a,required=True,type=Path)
    args=ap.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("Never overwrite an existing diagnostic candidate")
    result,info=apply(args.input.read_bytes())
    args.output.write_bytes(result)
    args.report.write_text(json.dumps(info,indent=2,sort_keys=True)+"\n")
    print(json.dumps(info,sort_keys=True))

if __name__=="__main__":main()
