"""r67.14u: adapt original companion EVENT text Y to its native bubble variant.

Runtime ownership proof (r67.14q disassembly):
- H_TalkBuddyTask text wrappers at 0x963D20 / 0x963DFC use constant
  f13=280 / f13=300 for ALL <0x259 event comments.
- Bubble sprites at 0x166070-0x166134 index s0+0x2F8, which is 0 or 1.
- Native geometry table at EE 0x4F8D9C and 0x4F8DC4 has Y=172 when
  index=0, Y=230 when index=1, a precise 58-unit displacement.
- Consequently the legacy fixed Y anchors fit lower index 1 but cause
  the same English rows to descend toward/beyond the frame for index 0.

Preserve lower-bubble (user approved) 280/300 verbatim. Select 222/242
for the upper bubble only (relative content inset 50/70 unchanged).

The ONLY q-protected bytes intentionally amended are the two wrapper Y-load
instructions, converted to JALs into private helpers. This is a specifically
requested new corrective scope; immutable q approval manifest IS NOT edited.
Strict q lock is EXPECTED to reject those exact two words. Replacements
must be verified with narrowly bounded scoped-preservation audit.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.r67_chamber_story_text_only import (
    Assembly, ELF_SEGMENT_FO, ELF_SEGMENT_VA, ELF_SEGMENT_RESERVE,
    ELF_BIAS, _i, _r, _jal, _float_word,
)
from tools.r67_lion_statue_ui import sha
from tools.r67_14t_stone_tablet_fit import assert_all_tablets_fit

SOURCE_T_SHA = "062689efed67a83f24f7524cedb50a21505ce6431f456fc196961d98cd434a3d"
EVENT_Y_WRAPPERS = ((0x963D78, 280.0, 222.0), (0x963E54, 300.0, 242.0))
GEOMETRY_Y = (172.0, 230.0)
RUNTIME_BUBBLE_VARIANT_OFFSET = 0x2F8
REQUIRED_DIFF = 58.0
SEGMENT_ALIGNMENT = 4
ORIGINAL_VISUALLY_APPROVED_TWO_ROWS = (
    "Make sure you're always ready to",
    "switch into battle mode anytime.",
)

def text_y_helper(lower_y:float,upper_y:float)->bytes:
    a=Assembly()
    a.emit(_i(33, 16, 8, RUNTIME_BUBBLE_VARIANT_OFFSET)) # lh t0,0x2f8(s0)
    a.branch(5,8,0,"lower")                              # bnez t0,lower
    a.emit(0)
    a.const(8,_float_word(upper_y))
    a.branch(4,0,0,"done")
    a.emit(0)
    a.label("lower")
    a.const(8,_float_word(lower_y))
    a.label("done")
    a.emit((17<<26)|(4<<21)|(8<<16)|(13<<11))          # mtc1 t0,f13
    a.emit(_r(31,0,0,0,8))                            # jr ra
    a.emit(0)
    return a.done()

def preimage_event(elf:bytes)->None:
    fo,va,sz,memsz=(struct.unpack_from("<I",elf,i)[0] for i in (0x58,0x5c,0x64,0x68))
    if (fo,va,fo+sz,memsz)!=(ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(elf),ELF_SEGMENT_RESERVE):
        raise ValueError("Wrong translated-ELF reservation or layout")
    # Read the exact *native immutable* background-geometry tables, NOT
    # inferred ratios from screenshots. The first & second 20-byte records:
    # [sprite_kind, sprite_id, float(x), float(y), float(width)].
    expected=( (0x02,0x68,249.0,172.0,346.0),
               (0x02,0x69,249.0,230.0,346.0) )
    for idx,(kind,id,x,y,w) in enumerate(expected):
        off=0x4f8d9c + idx*20 - ELF_BIAS
        rec=struct.unpack_from("<2I3f",elf,off)
        if rec!=(kind,id,x,y,w):
            raise ValueError(f"Native event bubble variant {idx} data drifted: {rec!r}")
    for va,y,upper in EVENT_Y_WRAPPERS:
        off=ELF_SEGMENT_FO+va-ELF_SEGMENT_VA
        wanted=_i(15,0,8,_float_word(y)>>16)
        if struct.unpack_from("<I",elf,off)[0]!=wanted:
            raise ValueError(f"Approved {va:#x} Y-load preimage changed")
        if struct.unpack_from("<I",elf,off+4)[0]!=(17<<26)|(4<<21)|(8<<16)|(13<<11):
            raise ValueError(f"Approved {va:#x} mtc1 Y-load delay slot changed")
        if y-upper!=REQUIRED_DIFF or y-GEOMETRY_Y[1]!=upper-GEOMETRY_Y[0]:
            raise ValueError("Original relative bubble-text geometry not preserved")

def apply(source:bytes)->tuple[bytes,dict]:
    if sha(source)!=SOURCE_T_SHA:
        raise ValueError("Unexpected r67.14t source; no reapplication or cross-branch patch")
    preimage_event(source)
    data=bytearray(source)
    while len(data)%SEGMENT_ALIGNMENT:data.append(0)
    helpers=[]
    allowed=set(range(0x64,0x68))
    for site,lower,upper in EVENT_Y_WRAPPERS:
        target=ELF_SEGMENT_VA+len(data)-ELF_SEGMENT_FO
        helper=text_y_helper(lower,upper)
        if target&3 or len(data)+len(helper)-ELF_SEGMENT_FO>ELF_SEGMENT_RESERVE:
            raise ValueError("Private event Y helper would exceed executable reservation")
        data.extend(helper)
        off=ELF_SEGMENT_FO+site-ELF_SEGMENT_VA
        struct.pack_into("<I",data,off,_jal(target))
        allowed.update(range(off,off+4))
        helpers.append({"protected_original_va":hex(site),"adaptive_private_va":hex(target),
                        "helper_size_bytes":len(helper),"lower_y":lower,"upper_y":upper})
    struct.pack_into("<I",data,0x64,len(data)-ELF_SEGMENT_FO)
    modified=[i for i,(a,b) in enumerate(zip(source,data)) if a!=b]
    if not modified or set(modified)-allowed:
        raise ValueError(f"Unclassified original ELF changes: {set(modified)-allowed}")
    result=bytes(data)
    assert_all_tablets_fit(result)
    return result,{
        "revision":"r67.14u","status":"DIAGNOSTIC_USER_GAMEPLAY_APPROVAL_REQUIRED",
        "source_elf_sha256":SOURCE_T_SHA,"candidate_elf_sha256":sha(result),
        "native_bubble_geometry_y":[172.0,230.0],
        "invariant_relative_text_insets":[50.0,70.0],
        "event_variant_field":"s0+0x2F8",
        "event_wrapper_y_adapters":helpers,
        "q_immutable_manifest_modified":False,
        "q_private_owner_new_scope":"two Y-load words only, explicit user request to restore approved dialog placement",
        "newly_approved_lion_or_tablet_modifications":False,
        "original_elf_changed_offsets":[hex(x) for x in modified],
        "appended_bytes":len(result)-len(source),
        "afk_and_global_font_code_modified":False,
        "save_serialization_modified":False,
        "runtime_verified":False,"release_approved":False,
    }

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("input","output","report"):p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():
        raise FileExistsError("Refuse to overwrite diagnostic artifacts")
    output,report=apply(a.input.read_bytes())
    a.output.write_bytes(output)
    a.report.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":main()
