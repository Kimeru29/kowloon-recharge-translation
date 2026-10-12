"""r67.14v: FIX ONLY the 2-line opening companion dialogue for upper bubble.

The previously approved 'Eerie place.' single-line bubble can use variant=0
and already rendered correctly. Do not touch its Y placement or any other
original companion event. The 58-unit native geometry variant adjustment
applies only when input text pointer is the opening dialogue's exact first
or second PS4 translation alias (0x963F00, 0x963F8C) AND native bubble index
task+0x2F8 == 0. Lower variant always retains q's approved 280/300. All
other comments, including Eerie, retain q's approved Y even in variant 0.
"""
from __future__ import annotations
import argparse,json,struct
from pathlib import Path
from tools.r67_chamber_story_text_only import (
    Assembly,ELF_SEGMENT_FO,ELF_SEGMENT_VA,ELF_SEGMENT_RESERVE,
    _i,_r,_jal,_float_word,
)
from tools.r67_14u_companion_bubble_relative_y import (
    SOURCE_T_SHA,EVENT_Y_WRAPPERS,RUNTIME_BUBBLE_VARIANT_OFFSET,
    GEOMETRY_Y,REQUIRED_DIFF,preimage_event,
)
from tools.r67_lion_statue_ui import sha
from tools.r67_14t_stone_tablet_fit import assert_all_tablets_fit
from tools.r67_14q_approved_lock import MANIFEST,verify_approved

OPENING_SOURCE_POINTERS=(0x963F00,0x963F8C)
EERIE_SOURCE_POINTER=0x9630BA
ORIGINAL_POINTER_SLOTS=(0x3D3438,0x3D343C)
EERIE_SOURCE_SLOT=0x3D3428

def text_y_helper(lower_y:float,upper_y:float)->bytes:
    a=Assembly()
    a.emit(_i(33,16,8,RUNTIME_BUBBLE_VARIANT_OFFSET)) # lh t0,0x2f8(s0)
    a.branch(5,8,0,"lower")                           # lower bubble? preserve
    a.emit(0)
    for ptr in OPENING_SOURCE_POINTERS:
        a.const(8,ptr)
        a.branch(4,9,8,"upper")                         # beq t1,t0,upper
        a.emit(0)
    a.branch(4,0,0,"lower")                             # unrelated source
    a.emit(0)
    a.label("upper")
    a.const(8,_float_word(upper_y))
    a.branch(4,0,0,"done")
    a.emit(0)
    a.label("lower")
    a.const(8,_float_word(lower_y))
    a.label("done")
    a.emit((17<<26)|(4<<21)|(8<<16)|(13<<11))          # mtc1 t0,f13
    a.emit(_r(31,0,0,0,8))
    a.emit(0)
    return a.done()

def apply(source:bytes)->tuple[bytes,dict]:
    if sha(source)!=SOURCE_T_SHA:raise ValueError("Only exact r67.14t source allowed")
    preimage_event(source)
    for pos,ptr in zip(ORIGINAL_POINTER_SLOTS,OPENING_SOURCE_POINTERS,strict=True):
        if struct.unpack_from("<I",source,pos)[0]!=ptr:
            raise ValueError(f"Opening English source pointer drift at {pos:#x}")
    if struct.unpack_from("<I",source,EERIE_SOURCE_SLOT)[0]!=EERIE_SOURCE_POINTER:
        raise ValueError("Eerie place.'s previously approved source pointer drift")
    verify_approved(source,json.loads(MANIFEST.read_text()))
    out=bytearray(source)
    while len(out)&3:out.append(0)
    allow=set(range(0x64,0x68))
    helpers=[]
    for site,lower,upper in EVENT_Y_WRAPPERS:
        target=ELF_SEGMENT_VA+len(out)-ELF_SEGMENT_FO
        bytecode=text_y_helper(lower,upper)
        if target&3 or len(out)+len(bytecode)-ELF_SEGMENT_FO>ELF_SEGMENT_RESERVE:
            raise ValueError("Private dialogue hook outside reserved ELF segment")
        out.extend(bytecode)
        off=ELF_SEGMENT_FO+site-ELF_SEGMENT_VA
        struct.pack_into("<I",out,off,_jal(target))
        allow.update(range(off,off+4))
        helpers.append(dict(site=hex(site),helper_va=hex(target),helper_size=len(bytecode),
                            lower_bubble_y=lower,opening_upper_bubble_y=upper))
    struct.pack_into("<I",out,0x64,len(out)-ELF_SEGMENT_FO)
    changed=[i for i,(a,b) in enumerate(zip(source,out)) if a!=b]
    if not changed or set(changed)-allow:
        raise ValueError(f"Non-approved previous executable bytes modified: {set(changed)-allow}")
    result=bytes(out)
    assert_all_tablets_fit(result)
    return result,{
        "release":"r67.14v","status":"DIAGNOSTIC_AWAITING_USER_GAMEPLAY_APPROVAL",
        "prior_r67_14t_elf_sha256":SOURCE_T_SHA,"candidate_elf_sha256":sha(result),
        "relative_bubble_native_delta":REQUIRED_DIFF,
        "native_variant_selector":"s0+0x2f8",
        "opening_specific_source_pointers":list(map(hex,OPENING_SOURCE_POINTERS)),
        "other_companion_events_unchanged_even_on_upper_variant":True,
        "eerie_place_unchanged_on_both_bubble_variants":True,
        "lower_original_user_approved_geometry_unchanged":True,
        "helpers":helpers,"changed_original_offsets":[hex(x) for x in changed],
        "appended_bytes":len(result)-len(source),
        "prior_user_approved_item_tablet_owners_unchanged":True,
        "immutable_q_manifest_unmodified":True,
        "strict_q_lock_candidate_expected_scoped_failure":True,
        "runtime_verified":False,"cross_release_save_runtime_verified":False,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("input","output","report"):p.add_argument("--"+n,type=Path,required=True)
    x=p.parse_args()
    if x.output.exists() or x.report.exists():raise FileExistsError("No prior release overwrite")
    out,report=apply(x.input.read_bytes())
    x.output.write_bytes(out)
    x.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
