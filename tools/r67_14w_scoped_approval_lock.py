"""r67.14w fail-closed scoped approval lock: ONE native event construction JAL.

The immutable q owner region is intentionally changed at 0x16606C.
Recreate that one original instruction ONLY in memory, then run the entire
original q AND t approved locks on the staged/installed executable.
Never regenerate previous manifests or weaken earlier approvals.
"""
from __future__ import annotations
import json,struct
from pathlib import Path
from tools.r67_14w_restore_opening_bubble_shape import (
    SOURCE_T_SHA,ORIGINAL_RECONSTRUCTION_STORE_VA,ORIGINAL_RECONSTRUCTION_STORE,
    NATIVE_DELAY_SLOT_VA,NATIVE_DELAY_SLOT,NATIVE_NEXT_VA,NATIVE_NEXT_WORD,
    preimage,make_geometry_helper,
)
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO,ELF_SEGMENT_VA,ELF_BIAS,_jal
from tools.r67_14t_approved_ui_lock import verify_ui,MANIFEST as T_MANIFEST
from tools.r67_14q_approved_lock import verify_approved,MANIFEST as Q_MANIFEST
from tools.r67_lion_statue_ui import sha

SOURCE_T_INSTALLED_SHA="f29cb00fa819bdcc82b91d62f889c09f547ad4811f734295c7843a8cb080518a"

def validate_scoped(candidate:bytes,reference:bytes)->dict:
    if sha(reference) not in (SOURCE_T_SHA,SOURCE_T_INSTALLED_SHA):
        raise ValueError("Source is neither approved staged nor installed t ELF")
    preimage_staged=sha(reference)==SOURCE_T_SHA
    # The installed q/t copy has relocated ROFS bytes, so preimage() only
    # accepts staged source; all event/geometry offsets are identical.
    if preimage_staged:preimage(reference)
    expected_original=ORIGINAL_RECONSTRUCTION_STORE_VA-ELF_BIAS
    expected_words=((ORIGINAL_RECONSTRUCTION_STORE_VA,ORIGINAL_RECONSTRUCTION_STORE),
                    (NATIVE_DELAY_SLOT_VA,NATIVE_DELAY_SLOT),
                    (NATIVE_NEXT_VA,NATIVE_NEXT_WORD))
    for site,want in expected_words:
        if struct.unpack_from("<I",reference,site-ELF_BIAS)[0]!=want:
            raise ValueError(f"Previous approved event reconstruction drift {site:#x}")
    if len(candidate)<=len(reference):
        raise ValueError("Candidate is not append-only")
    pad=(-len(reference))%4
    helper=make_geometry_helper()
    if len(candidate)-len(reference)!=pad+len(helper):
        raise ValueError("Private helper size changed from expected geometry-only patch")
    helper_start=len(reference)+pad
    helper_va=ELF_SEGMENT_VA+helper_start-ELF_SEGMENT_FO
    site=expected_original
    if struct.unpack_from("<I",candidate,site)[0]!=_jal(helper_va):
        raise ValueError("Opening event native construction JAL does not target guarded helper")
    if candidate[helper_start:helper_start+len(helper)]!=helper:
        raise ValueError("Opening-only geometry helper deviates from audited machine code")
    if candidate[len(reference):helper_start]!=bytes(pad):
        raise ValueError("Unexpected executable helper padding")
    if struct.unpack_from("<I",candidate,0x64)[0]!=len(candidate)-ELF_SEGMENT_FO:
        raise ValueError("ELF private PT_LOAD length drift")
    allowed=set(range(0x64,0x68))
    allowed.update(range(site,site+4))
    diffs=[i for i,(a,b) in enumerate(zip(reference,candidate)) if a!=b]
    if not diffs or set(diffs)-allowed:
        raise ValueError(f"Unclassified original approved executable changes {set(diffs)-allowed}")
    reconstructed=bytearray(candidate)
    reconstructed[site:site+4]=reference[site:site+4]
    # Every word/byte of the immutable q approval region except this one
    # MUST remain exact. The program header and appended private helper may
    # grow, but the q-lock's fixed approved regions remain byte-identical.
    original_q=verify_approved(bytes(reconstructed),json.loads(Q_MANIFEST.read_text()))
    original_t=verify_ui(bytes(reconstructed),json.loads(T_MANIFEST.read_text()))
    if original_q["approved_regions"]!=4 or original_t["all_registered_tablets"]!=58:
        raise ValueError("Earlier approved presentation owners changed")
    return {
        "status":"PASS_ONE_EXACT_OPENING_EVENT_CONSTRUCTION_EXCEPTION",
        "approved_original_q_regions":4,
        "approved_original_t_ui":original_t["status"],
        "lion_item_fit_scale":original_t["lion_approved_horizontal_scale"],
        "all_native_stone_tablets":original_t["all_registered_tablets"],
        "all_stone_inscription_rows":original_t["all_inscription_rows_checked"],
        "original_q_and_t_manifest_unchanged":True,
        "restored_prior_event_native_instruction_in_memory_only":hex(ORIGINAL_RECONSTRUCTION_STORE_VA),
        "native_original_delay_slot_preserved":True,
        "private_helper_va":hex(helper_va),
        "private_helper_size":len(helper),
        "other_original_executable_bytes_modified":0,
        "modified_existing_offsets":[hex(i) for i in diffs],
        "runtime_approved":False
    }
