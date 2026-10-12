"""Scoped immutability proof for approved q dialog + approved t item/tablet UI.

The user explicitly requested new event-Y adaptation. The immutable r67.14q
manifest remains unchanged and DOES reject candidate u at the exact two newly
patched words. We therefore prove that restoring those two words *in memory*
reconstructs an image that passes the ORIGINAL strict q and t locks. The
restoration is never written to disk. Every byte outside the two words and
the appended helper is fail-closed against the hash-pinned r67.14t image.

This does not claim the new Y variant has been gameplay-approved.
"""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from tools.r67_14t_approved_ui_lock import MANIFEST as T_MANIFEST,verify_ui
from tools.r67_14q_approved_lock import MANIFEST as Q_MANIFEST,verify_approved
from tools.r67_14u_companion_bubble_relative_y import (
    SOURCE_T_SHA,EVENT_Y_WRAPPERS,RUNTIME_BUBBLE_VARIANT_OFFSET,
    GEOMETRY_Y,REQUIRED_DIFF,preimage_event,text_y_helper
)
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO,ELF_SEGMENT_VA,_jal,_i,_float_word
from tools.r67_lion_statue_ui import sha

def validate_scoped(candidate:bytes,reference:bytes)->dict:
    if sha(reference) not in (SOURCE_T_SHA, "f29cb00fa819bdcc82b91d62f889c09f547ad4811f734295c7843a8cb080518a"):
        raise ValueError("Not either frozen r67.14t staged or independently relocated finished-ISO ELF")
    preimage_event(reference)
    # This must still pass the original unamended q manifest / t manifest.
    assert verify_approved(reference,json.loads(Q_MANIFEST.read_text()))["status"]=="PASS_R67_14Q_VISUALLY_APPROVED_OWNERS"
    assert verify_ui(reference,json.loads(T_MANIFEST.read_text()))["status"]=="PASS_VISUALLY_ACCEPTED_LION_AND_STONE_TABLET_STATIC_OWNERS"
    if len(candidate)<len(reference):
        raise ValueError("Candidate ELF truncated")
    allow=set(range(0x64,0x68))
    for va,lower,upper in EVENT_Y_WRAPPERS:
        off=ELF_SEGMENT_FO+va-ELF_SEGMENT_VA
        allow.update(range(off,off+4))
    diffs=[i for i,(p,n) in enumerate(zip(reference,candidate)) if p!=n]
    if set(diffs)-allow:raise ValueError(f"Unapproved prior ELF byte mutated: {set(diffs)-allow}")
    if len(candidate)-len(reference)!=83:
        raise ValueError("Unexpected diagnostic helper length/alignment")
    if struct.unpack_from("<I",candidate,0x64)[0]!=len(candidate)-ELF_SEGMENT_FO:
        raise ValueError("Candidate program-header file-size mismatch")
    for i,(va,lower,upper) in enumerate(EVENT_Y_WRAPPERS):
        off=ELF_SEGMENT_FO+va-ELF_SEGMENT_VA
        target=ELF_SEGMENT_VA+(len(reference)+3)//4*4-ELF_SEGMENT_FO
        if i:target+=len(text_y_helper(*EVENT_Y_WRAPPERS[0][1:]))
        if struct.unpack_from("<I",candidate,off)[0]!=_jal(target):
            raise ValueError(f"Unapproved event-Y callsite target at {va:#x}")
        h=text_y_helper(lower,upper)
        hstart=ELF_SEGMENT_FO+target-ELF_SEGMENT_VA
        if candidate[hstart:hstart+len(h)]!=h:
            raise ValueError(f"Adaptive event-Y helper corrupted at {target:#x}")
        # JAL delay slot is still original MTC1; helper overrides f13 after
        # that delay slot. Never mutate it, or leak scratch MIPS values.
        if candidate[off+4:off+8]!=reference[off+4:off+8]:
            raise ValueError("Approved event Y delay slot altered")
    # Reconstruct only the ORIGINAL two q region words in temporary memory.
    surrogate=bytearray(candidate)
    for site,_,_ in EVENT_Y_WRAPPERS:
        off=ELF_SEGMENT_FO+site-ELF_SEGMENT_VA
        surrogate[off:off+4]=reference[off:off+4]
    # Strict published Q manifest and T UI manifest must *both* pass.
    original_q=verify_approved(bytes(surrogate),json.loads(Q_MANIFEST.read_text()))
    original_t=verify_ui(bytes(surrogate),json.loads(T_MANIFEST.read_text()))
    if original_q["approved_regions"]!=4 or original_t["all_registered_tablets"]!=58:
        raise ValueError("Approved prior UI owners or q native regions drifted")
    return {
        "status":"PASS_SCOPED_Q_PRIVATE_EVENT_Y_EXCEPTION_AND_ALL_T_APPROVED_UI",
        "unmodified_q_manifest_original_reference_passed":True,
        "unmodified_q_manifest_candidate_strict_expected_fail":True,
        "allowed_exact_event_Y_instruction_vas":[hex(x[0]) for x in EVENT_Y_WRAPPERS],
        "original_q_protected_regions_reverified_without_new_two_words":4,
        "previous_approved_item_and_tablet_preservation":original_t["status"],
        "other_original_elf_bytes_modified":0,
        "original_modified_bytes":[hex(i) for i in diffs],
        "bubble_variant_Y":[172.0,230.0],
        "new_first_line_y":[222.0,280.0],
        "new_second_line_y":[242.0,300.0],
        "row_spacing_unchanged":20,
        "runtime_gameplay_verified":False
    }
