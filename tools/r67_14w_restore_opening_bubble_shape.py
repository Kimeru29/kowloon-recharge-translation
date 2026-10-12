"""r67.14w: restore native shared bubble geometry ONLY for opening event row.

Root cause: The previously assumed 58-unit *vertical* companion delta is
actually X/slot placement (172 vs 230), with a common native Y anchor=346.
Thus r67.14u/v incorrectly moved text upward. Original approved q event
Y=280/300 is already exactly correct for native green 288x80/pivotY77:
top = 346-77 = 269, leaving the accepted 11/31 text insets.

Normal L1 and AFK callers mutate shared 0x68/0x69 and 0x6A sprite geometry.
The original event constructor uses these resources WITHOUT first restoring
native dimensions, allowing stale (tall AFK or compact L1) geometry. Restore
those resources only for H_TalkBuddyTask event record 2, subrow 1: both
original strings 'Make sure ...' / 'switch into battle mode anytime.'.

Patch the original sw zero,0x5C(s0) at EE 0x16606C to JAL a private helper.
The next native lh v1,0x2F8(s0) remains the JAL delay slot, preserving the
slot for native resource creation at 0x166074. The helper performs the original
store, does NOT change v1, and uses only v0/a0/a1/a2, whose values are
overwritten by the native continuation. No text code, Y coordinates, AFK
specialized constructor, saved data or other record is changed.
"""
from __future__ import annotations
import argparse,json,struct
from pathlib import Path

from tools.r67_chamber_story_text_only import (
    Assembly,ELF_SEGMENT_FO,ELF_SEGMENT_VA,ELF_SEGMENT_RESERVE,ELF_BIAS,
    _i,_r,_jal,_float_word,
)
from tools.r67_lion_statue_ui import sha
from tools.r67_14t_stone_tablet_fit import assert_all_tablets_fit
from tools.r67_14q_approved_lock import verify_approved, MANIFEST as Q_MANIFEST

SOURCE_T_SHA = "062689efed67a83f24f7524cedb50a21505ce6431f456fc196961d98cd434a3d"
ORIGINAL_RECONSTRUCTION_STORE_VA=0x16606C
NATIVE_DELAY_SLOT_VA=0x166070
NATIVE_NEXT_VA=0x166074
ORIGINAL_RECONSTRUCTION_STORE=_i(43,16,0,0x5C)
NATIVE_DELAY_SLOT=_i(33,16,3,0x2F8)
NATIVE_NEXT_WORD=_r(0,3,2,2,0)
EVENT_RECORD_ID=2
EVENT_SUBROW_ID=1
OPENING_FIRST_PTR_OFFSET=0x3D3438
OPENING_SECOND_PTR_OFFSET=0x3D343C
OPENING_EXPECTED_POINTERS=(0x963F00,0x963F8C)
EERIE_PTR_OFFSET=0x3D3428
EERIE_PTR=0x9630BA
# The resource table's last two floats are X,Y. Both slots share Y=346.
GREEN_STATIC_VA=0x450AC4
BLUE_STATIC_VA=0x450B24
BLUE_FRAME_STRIDE=0x30
GREEN_NATIVE=(288.0,80.0,77.0)
GREEN_NATIVE_PIVOT_X=(67.0,125.0)
BLUE_NATIVE=(288.0,56.0,67.0)
BLUE_NATIVE_PIVOT_Y=(74.0,75.0,76.0)


def preimage(source:bytes)->None:
    if sha(source)!=SOURCE_T_SHA:
        raise ValueError("Source must be exact user-approved r67.14t")
    hdr=struct.unpack_from("<8I",source,0x54)
    if (hdr[0],hdr[1],hdr[2],hdr[1]+hdr[4],hdr[5],hdr[6],hdr[7])!=(
        1,ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(source),ELF_SEGMENT_RESERVE,7,16
    ):
        raise ValueError("Original PS2 private ELF PT_LOAD mismatch")
    for va,word in ((ORIGINAL_RECONSTRUCTION_STORE_VA,ORIGINAL_RECONSTRUCTION_STORE),
                    (NATIVE_DELAY_SLOT_VA,NATIVE_DELAY_SLOT),
                    (NATIVE_NEXT_VA,NATIVE_NEXT_WORD)):
        if struct.unpack_from("<I",source,va-ELF_BIAS)[0]!=word:
            raise ValueError(f"Native event bubble reconstruction preimage drift at {va:#x}")
    for offset,wanted in zip((OPENING_FIRST_PTR_OFFSET,OPENING_SECOND_PTR_OFFSET),
                             OPENING_EXPECTED_POINTERS,strict=True):
        if struct.unpack_from("<I",source,offset)[0]!=wanted:
            raise ValueError(f"Opening event translation alias drift at {offset:#x}")
    if struct.unpack_from("<I",source,EERIE_PTR_OFFSET)[0]!=EERIE_PTR:
        raise ValueError("Eerie place. event pointer was changed")
    # These values are sprite pivot/shape, not screen text coordinates.
    for n in range(2):
        off=GREEN_STATIC_VA+BLUE_FRAME_STRIDE*n-ELF_BIAS
        expected=(GREEN_NATIVE[0],GREEN_NATIVE[1],GREEN_NATIVE_PIVOT_X[n],GREEN_NATIVE[2])
        if struct.unpack_from("<4f",source,off)!=expected:
            raise ValueError(f"Native static green geometry preimage drift slot {n}")
    for n in range(3):
        off=BLUE_STATIC_VA+BLUE_FRAME_STRIDE*n-ELF_BIAS
        expected=(BLUE_NATIVE[0],BLUE_NATIVE[1],BLUE_NATIVE[2],BLUE_NATIVE_PIVOT_Y[n])
        if struct.unpack_from("<4f",source,off)!=expected:
            raise ValueError(f"Native blue metadata drift frame {n}")
    # Proof the 58-unit difference is X, not Y.
    for n,expected_x in enumerate((172.0,230.0)):
        placement=struct.unpack_from("<2I3f",source,0x3F8E1C+n*20)
        if placement!=(2,0x68+n,249.0,expected_x,346.0):
            raise ValueError("Companion slot X/Y placement record drift")
    approved=verify_approved(source,json.loads(Q_MANIFEST.read_text()))
    if approved["approved_regions"]!=4:
        raise ValueError("Previous strict q baseline failed")


def make_geometry_helper()->bytes:
    a=Assembly()
    a.emit(ORIGINAL_RECONSTRUCTION_STORE)               # originally overwritten sw
    a.emit(_i(33,16,2,4))                               # lh v0,record id
    a.emit(_i(9,0,4,EVENT_RECORD_ID))                   # a0 = 2
    a.branch(5,2,4,"done")                              # only event record 2
    a.emit(0)
    a.emit(_i(33,16,2,0xA))                            # lh v0,subrow
    a.emit(_i(9,0,4,EVENT_SUBROW_ID))                   # a0=1
    a.branch(5,2,4,"done")                              # only two-line opening
    a.emit(0)
    a.emit(_i(11,3,2,2))                               # sltiu v0,v1,2
    a.branch(4,2,0,"done")                              # invalid slot: no write
    a.emit(0)
    a.emit(_r(0,3,2,4,0))                              # sll v0,v1,4
    a.emit(_r(0,3,4,5,0))                              # sll a0,v1,5
    a.emit(_r(2,4,2,0,33))                             # v0 = slot*48
    a.const(5,GREEN_STATIC_VA)
    a.emit(_r(5,2,5,0,33))                             # selected green width ptr
    a.const(6,_float_word(GREEN_NATIVE[0]))
    a.emit(_i(43,5,6,0))                               # sw 288,width
    a.const(6,_float_word(GREEN_NATIVE[1]))
    a.emit(_i(43,5,6,4))                               # sw 80,height
    a.const(6,_float_word(GREEN_NATIVE[2]))
    a.emit(_i(43,5,6,12))                              # sw 77,pivotY
    a.const(6,_float_word(GREEN_NATIVE_PIVOT_X[0]))
    a.branch(4,3,0,"green_pivot_ready")
    a.emit(0)
    a.const(6,_float_word(GREEN_NATIVE_PIVOT_X[1]))
    a.label("green_pivot_ready")
    a.emit(_i(43,5,6,8))                               # sw pivotX=67/125
    a.const(5,BLUE_STATIC_VA)
    for value,indices in (
        (BLUE_NATIVE[0],(0,0x30,0x60)),
        (BLUE_NATIVE[1],(4,0x34,0x64)),
        (BLUE_NATIVE[2],(8,0x38,0x68)),
    ):
        a.const(6,_float_word(value))
        for disp in indices:a.emit(_i(43,5,6,disp))
    for frame,value in enumerate(BLUE_NATIVE_PIVOT_Y):
        a.const(6,_float_word(value))
        a.emit(_i(43,5,6,0xC+frame*BLUE_FRAME_STRIDE))
    a.label("done")
    a.emit(_r(31,0,0,0,8))
    a.emit(0)
    return a.done()


def apply(source:bytes)->tuple[bytes,dict]:
    preimage(source)
    buffer=bytearray(source)
    while len(buffer)%4:buffer.append(0)
    helper_va=ELF_SEGMENT_VA+len(buffer)-ELF_SEGMENT_FO
    helper=make_geometry_helper()
    if helper_va&3 or len(buffer)+len(helper)-ELF_SEGMENT_FO>ELF_SEGMENT_RESERVE:
        raise ValueError("Native geometry helper exceeds reserved translation segment")
    buffer.extend(helper)
    struct.pack_into("<I",buffer,ORIGINAL_RECONSTRUCTION_STORE_VA-ELF_BIAS,_jal(helper_va))
    struct.pack_into("<I",buffer,0x64,len(buffer)-ELF_SEGMENT_FO)
    old_changed=[idx for idx,(x,y) in enumerate(zip(source,buffer)) if x!=y]
    allowed=set(range(0x64,0x68))
    allowed.update(range(ORIGINAL_RECONSTRUCTION_STORE_VA-ELF_BIAS,ORIGINAL_RECONSTRUCTION_STORE_VA-ELF_BIAS+4))
    if not old_changed or set(old_changed)-allowed:
        raise ValueError(f"Unexpected old ELF mutations {set(old_changed)-allowed}")
    candidate=bytes(buffer)
    assert_all_tablets_fit(candidate)
    return candidate,{
        "release":"r67.14w","status":"DIAGNOSTIC_PENDING_NEW_SCREENSHOT",
        "source_approved_t_sha256":SOURCE_T_SHA,"candidate_elf_sha256":sha(candidate),
        "root_cause":"slot 58 offset is native X not Y; event constructor never restores dynamically mutated shared speech resources",
        "native_green_pivot_placement_slot_xy":[[172,346],[230,346]],
        "opening_record_id":EVENT_RECORD_ID,"opening_subrow_id":EVENT_SUBROW_ID,
        "original_opening_first_y":280.0,"original_opening_second_y":300.0,
        "unmodified_Eerie_place_and_other_dialogues":True,
        "green_restored_shape":[288,80],"green_pivot_y":77,
        "blue_restored_shape":[288,56],"blue_animation_frame_pivot_y":[74,75,76],
        "native_event_reconstruction_site":hex(ORIGINAL_RECONSTRUCTION_STORE_VA),
        "original_native_delay_slot_preserved":True,
        "private_geometry_helper_va":hex(helper_va),"helper_bytes":len(helper),
        "modified_old_elf_byte_offsets":list(map(hex,old_changed)),
        "appended_bytes":len(candidate)-len(source),
        "q_immutable_approval_manifest_changed":False,
        "q_locked_intentional_exception":"one original event bubble reconstruction word, restored only in memory during scoped preservation test",
        "save_serialization_modified":False,
        "runtime_verified":False,"release_approved":False,
    }


def main()->None:
    a=argparse.ArgumentParser(description=__doc__)
    for key in ("input","output","report"):a.add_argument("--"+key,type=Path,required=True)
    x=a.parse_args()
    if x.output.exists() or x.report.exists():
        raise FileExistsError("Previous diagnostic must not be overwritten")
    result,report=apply(x.input.read_bytes())
    x.output.write_bytes(result)
    x.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":
    main()
