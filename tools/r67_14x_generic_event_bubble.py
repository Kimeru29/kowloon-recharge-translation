"""r67.14x: full 601-record native event companion bubble shape normalization.

All ORIGINAL 0..600 H_TalkBuddyTask companion event comments use the same
two green 0x68/0x69 & blue 0x6A sprite consumers; unlike the dedicated AFK
path they do not restore their shared metadata after normal L1 action/AFK
uses. r67.14w guarded only record 2, subrow 1, leaving other event text
vulnerable to stale (compact/tall) shared speech resource geometry.

This reusable geometry-on-construction invariant replaces the SAME single
native executable reconstruction instruction as diagnostic w, starting
again from the EXACT user-approved r67.14t baseline (not from rejected
r67.14v nor record-specific r67.14w). The only switch is native
record-index < 0x259, matching documented separate AFK (>=0x259) owner.
All event records, both text rows & both companion slots share ONE geometry
helper with NO per-record/source-pointer exceptions. Existing event text
Y=280/300, font advances, two-line state/timers and native AFK hook unchanged.
"""
from __future__ import annotations
import argparse,json,struct
from pathlib import Path
from tools.r67_chamber_story_text_only import (
    Assembly, ELF_SEGMENT_FO,ELF_SEGMENT_VA,ELF_SEGMENT_RESERVE,ELF_BIAS,
    _i,_r,_jal,_float_word,
)
from tools.r67_lion_statue_ui import sha
from tools.r67_14t_stone_tablet_fit import assert_all_tablets_fit
from tools.r67_14w_restore_opening_bubble_shape import (
    preimage, SOURCE_T_SHA, ORIGINAL_RECONSTRUCTION_STORE_VA,
    ORIGINAL_RECONSTRUCTION_STORE, NATIVE_DELAY_SLOT_VA,NATIVE_DELAY_SLOT,
    NATIVE_NEXT_VA,NATIVE_NEXT_WORD,
    GREEN_STATIC_VA, BLUE_STATIC_VA,BLUE_FRAME_STRIDE,
    GREEN_NATIVE,GREEN_NATIVE_PIVOT_X,BLUE_NATIVE,BLUE_NATIVE_PIVOT_Y,
)
from tools.r67_14q_approved_lock import verify_approved, MANIFEST as Q_MANIFEST
EVENT_FIRST_RECORD=0
EVENT_RECORD_END_EXCLUSIVE=0x259 # 601 events; 600 AFK records follow
AFK_FIRST_RECORD=0x259
AFK_RECORDS=600


def make_geometry_helper()->bytes:
    a=Assembly()
    a.emit(ORIGINAL_RECONSTRUCTION_STORE)                  # preserve original sw zero,0x5c(s0)
    a.emit(_i(33,16,2,4))                                 # lh v0,current record
    a.emit(_i(11,2,4,EVENT_RECORD_END_EXCLUSIVE))          # sltiu a0,v0,601
    a.branch(4,4,0,"done")                                 # AFK path untouched
    a.emit(0)
    a.emit(_i(11,3,2,2))                                  # sltiu v0,v1,2
    a.branch(4,2,0,"done")                                 # no writes for invalid slot
    a.emit(0)
    a.emit(_r(0,3,2,4,0))                                 # sll v0,v1,4
    a.emit(_r(0,3,4,5,0))                                 # sll a0,v1,5
    a.emit(_r(2,4,2,0,33))                                # addu v0,v0,a0 (slot*48)
    a.const(5,GREEN_STATIC_VA)
    a.emit(_r(5,2,5,0,33))
    for idx,value in ((0,GREEN_NATIVE[0]),(4,GREEN_NATIVE[1]),(12,GREEN_NATIVE[2])):
        a.const(6,_float_word(value))
        a.emit(_i(43,5,6,idx))
    a.const(6,_float_word(GREEN_NATIVE_PIVOT_X[0]))
    a.branch(4,3,0,"green_pivot_ready")
    a.emit(0)
    a.const(6,_float_word(GREEN_NATIVE_PIVOT_X[1]))
    a.label("green_pivot_ready")
    a.emit(_i(43,5,6,8))
    a.const(5,BLUE_STATIC_VA)
    for value,indices in (
        (BLUE_NATIVE[0],(0,0x30,0x60)),
        (BLUE_NATIVE[1],(4,0x34,0x64)),
        (BLUE_NATIVE[2],(8,0x38,0x68)),
    ):
        a.const(6,_float_word(value))
        for offset in indices:a.emit(_i(43,5,6,offset))
    for frame,pivot in enumerate(BLUE_NATIVE_PIVOT_Y):
        a.const(6,_float_word(pivot))
        a.emit(_i(43,5,6,0xC+frame*BLUE_FRAME_STRIDE))
    a.label("done")
    a.emit(_r(31,0,0,0,8))
    a.emit(0)
    return a.done()


def apply(source:bytes)->tuple[bytes,dict]:
    preimage(source) # exact r67.14t & original event / q protected byte preimage
    if sha(source)!=SOURCE_T_SHA:raise ValueError("Not the exact accepted r67.14t source")
    if AFK_FIRST_RECORD!=EVENT_RECORD_END_EXCLUSIVE or AFK_RECORDS!=600:
        raise ValueError("Native event/AFK record namespace changed")
    b=bytearray(source)
    while len(b)&3:b.append(0)
    helper_va=ELF_SEGMENT_VA+len(b)-ELF_SEGMENT_FO
    helper=make_geometry_helper()
    if helper_va&3 or len(b)+len(helper)-ELF_SEGMENT_FO>ELF_SEGMENT_RESERVE:
        raise ValueError("Generic event helper outside executable's reserved segment")
    b.extend(helper)
    struct.pack_into("<I",b,ORIGINAL_RECONSTRUCTION_STORE_VA-ELF_BIAS,_jal(helper_va))
    struct.pack_into("<I",b,0x64,len(b)-ELF_SEGMENT_FO)
    allowed=set(range(0x64,0x68))
    allowed.update(range(ORIGINAL_RECONSTRUCTION_STORE_VA-ELF_BIAS,
                         ORIGINAL_RECONSTRUCTION_STORE_VA-ELF_BIAS+4))
    changed=[i for i,(a,c) in enumerate(zip(source,b)) if a!=c]
    if not changed or set(changed)-allowed:
        raise ValueError("Unexpected original ELF byte mutation")
    result=bytes(b)
    assert_all_tablets_fit(result)
    return result,{
        "release":"r67.14x","status":"DIAGNOSTIC_AWAITING_GENERIC_RUNTIME_REPRODUCTION",
        "original_r67_14t_sha256":SOURCE_T_SHA,
        "candidate_elf_sha256":sha(result),
        "all_normal_event_record_ids":"0..600 inclusive",
        "event_records_covered":EVENT_RECORD_END_EXCLUSIVE,
        "afk_first_record":AFK_FIRST_RECORD,
        "afk_records_unchanged":AFK_RECORDS,
        "both_companion_slots":True,
        "all_event_subrows":True,
        "no_source_pointer_or_event_id_specific_exceptions":True,
        "unchanged_original_english_Y":[280,300],
        "native_green_sprite_geometry":[288,80,77],
        "native_blue_sprite_geometry":[288,56],
        "original_Event_dispatch_JAL_delay_slot_unchanged":True,
        "native_reconstruction_instruction":hex(ORIGINAL_RECONSTRUCTION_STORE_VA),
        "private_helper_va":hex(helper_va),"helper_bytes":len(helper),
        "modified_old_elf_offsets":[hex(i) for i in changed],
        "appended_bytes":len(result)-len(source),
        "save_serialization_modified":False,
        "original_q_manifest_unchanged":True,
        "gameplay_visual_approval":False
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("input","output","report"):p.add_argument("--"+name,required=True,type=Path)
    x=p.parse_args()
    if x.output.exists() or x.report.exists():raise FileExistsError("Refuse to overwrite existing release")
    candidate,report=apply(x.input.read_bytes())
    x.output.write_bytes(candidate)
    x.report.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
