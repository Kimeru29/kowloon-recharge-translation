"""r67.14m: deterministic automatic EVENT comment hold time (AFK untouched).

The state-11 H_TalkBuddyTask display timer lives at task+0x08. At 0x1662DC
the native shared continuation stores low16(v0), and v0 currently contains
a text-object pointer or source-table pointer. The user captured an
r67.14k Eerie place. savestate: task+0x2c=0x153053AC and the countdown
task+0x08=0x5399, exactly 19 ticks after initializing it with 0x53AC.
A pointer is not a legitimate frame-duration. The same low16 can be small
or negative, causing text to flash or remain too long.

We preserve original shared 0x1662DC (including transient AFK timer value),
replace ONLY the subsequent state-11 initialization at 0x1662E0/0x1662E4
with a private MIPS helper call, and route both AFK and event returns back
to 0x1662E8. The helper performs native state transition (state=11) for
all, but initializes 300 ticks (~5 seconds at nominal 60fps) ONLY if
task.record_id < 0x259, already the same engine event-vs-AFK predicate.
AFK's existing 0x1662F8 156-tick or 0x166320 240-tick overrides are
untouched; no AFK visual/text/timeout behavior changes. Existing event
X/Y spacing, bubble/blue backing and two-line handling remain bit-identical
to r67.14l. All line lengths are held for the same duration, including
zero-second-field records.

DIAGNOSTIC ONLY, requires user cold-boot real-game visual confirmation.
"""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path
from tools.r67_chamber_story_text_only import (
    ELF_BIAS, ELF_SEGMENT_FO, ELF_SEGMENT_VA, ELF_SEGMENT_RESERVE,
    _i, _r, _jal, Assembly
)
from tools.r67_chamber_pre_glyph_font_target import sha

SOURCE_SHA256 = "56e6c2043125c87cef25ae27a111751875a815a35090a2c6d34f76b8408aa612"
HOOK_VA = 0x1662E0
DELAY_VA = HOOK_VA + 4
ORIGINAL_STATE_VALUE = 11
ORIGINAL_STATE_SETUP = _i(9, 0, 2, ORIGINAL_STATE_VALUE)  # addiu v0,0,11
ORIGINAL_STATE_STORE = _i(41,16,2,2)                     # sh v0,2(s0)
ORIGINAL_SHARED_TIMER_STORE_VA = 0x1662DC
ORIGINAL_SHARED_TIMER_STORE = _i(41,16,2,8)
ORIGINAL_RECORD_LOAD = _i(33,16,2,4)
ORIGINAL_EVENT_CHECK = _i(10,2,2,0x259)
ORIGINAL_AFK_TIMER_OVERRIDE = _i(41,16,2,8)
EVENT_BOUNDARY = 0x259
EVENT_DURATION_FRAMES = 300

def timer_helper() -> bytes:
    a=Assembly()
    a.emit(ORIGINAL_STATE_SETUP)       # original v0 = state 11
    a.emit(ORIGINAL_STATE_STORE)       # state 11; both families
    a.emit(ORIGINAL_RECORD_LOAD)       # v0 = record id
    a.emit(_i(10,2,2,EVENT_BOUNDARY))  # slti v0,v0,601
    a.branch(4,2,0,"done")          # beqz v0,done (AFK unchanged)
    a.emit(0)
    a.emit(_i(9,0,2,EVENT_DURATION_FRAMES))
    a.emit(_i(41,16,2,8))            # sh v0,8(s0), EVENT ONLY
    a.label("done")
    a.emit(_r(31,0,0,0,8))           # jr ra
    a.emit(0)
    return a.done()

def apply(source: bytes) -> tuple[bytes, dict]:
    if sha(source)!=SOURCE_SHA256:
        raise ValueError("Refusing non-approved r67.14l source or reapplication")
    original=bytes(source);data=bytearray(source)
    expected={
        ORIGINAL_SHARED_TIMER_STORE_VA:ORIGINAL_SHARED_TIMER_STORE,
        HOOK_VA:ORIGINAL_STATE_SETUP,
        DELAY_VA:ORIGINAL_STATE_STORE,
        0x1662E8:ORIGINAL_RECORD_LOAD,
        0x1662EC:ORIGINAL_EVENT_CHECK,
        0x1662F8:_i(9,0,2,0x9c),          # AFK 156 ticks
        0x1662FC:ORIGINAL_AFK_TIMER_OVERRIDE,
        0x166320:_i(9,0,2,0xf0),          # AFK 240 tick branch
        0x166324:ORIGINAL_AFK_TIMER_OVERRIDE
    }
    for va,word in expected.items():
        actual=struct.unpack_from("<I",original,va-ELF_BIAS)[0]
        if actual!=word:
            raise ValueError(f"Native timer/AFK preimage drift {va:#x}: {actual:#x}, expected {word:#x}")
    fo,va,size,reserve,flags=(struct.unpack_from("<I",original,i)[0] for i in (0x58,0x5c,0x64,0x68,0x6c))
    if (fo,va,fo+size,reserve,flags)!=(ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(original),ELF_SEGMENT_RESERVE,7):
        raise ValueError("Unexpected original private ELF program header")
    while len(data)&3:data.append(0)
    helper_va=va+len(data)-fo
    helper=timer_helper()
    if helper_va>=0x10000000 or helper_va&3 or len(data)+len(helper)-fo>reserve:
        raise ValueError("Native JAL helper is unreachable or outside reserved segment")
    data.extend(helper)
    struct.pack_into("<I",data,HOOK_VA-ELF_BIAS,_jal(helper_va))
    struct.pack_into("<I",data,DELAY_VA-ELF_BIAS,0)       # delay NOP, helper writes state 11
    struct.pack_into("<I",data,0x64,len(data)-fo)
    changed=[i for i,(a,b) in enumerate(zip(original,data)) if a!=b]
    allowed=set(range(0x64,0x68))
    for site in (HOOK_VA,DELAY_VA):allowed.update(range(site-ELF_BIAS,site-ELF_BIAS+4))
    if not changed or set(changed)-allowed:
        raise ValueError("Unexpected change outside state hook and ELF-size metadata")
    return bytes(data),dict(
        revision="r67.14m",status="DIAGNOSTIC_AWAITING_GAMEPLAY",
        source_r67_14l_sha256=sha(original),output_elf_sha256=sha(data),
        private_helper_va=hex(helper_va),helper_bytes=len(helper),
        changed_existing_byte_offsets=[hex(i) for i in changed],
        event_hold_frames=EVENT_DURATION_FRAMES,nominal_hold_seconds=EVENT_DURATION_FRAMES/60,
        event_predicate="native record ID < 0x259, all companion event comments",
        afk_native_timer_override_156_and_240_unchanged=True,
        afk_native_renderer_unchanged=True,event_script_geometry_unchanged=True,
        user_afk_states_preserved=True,user_visual_approved=False
    )

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ("input","output","report"):p.add_argument("--"+flag,required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():
        raise FileExistsError("Refusing to overwrite previous diagnostic")
    out,info=apply(a.input.read_bytes())
    a.output.write_bytes(out)
    a.report.write_text(json.dumps(info,sort_keys=True,indent=2)+"\n")
    print(json.dumps(info,sort_keys=True))
if __name__=="__main__":main()
