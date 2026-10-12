"""r67.14y approval freeze and explicit-owner r67.14z exception validator."""
from __future__ import annotations

import hashlib,json,struct
from pathlib import Path
from tools.r67_14q_approved_lock import MANIFEST as Q,verify_approved
from tools.r67_14t_approved_ui_lock import MANIFEST as T,verify_ui
from tools.r67_14y_inspection_save import validate_result as validate_y_inspections
from tools.r67_14y_release import verify_save_identity
from tools.r67_14t_stone_tablet_fit import assert_all_tablets_fit

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'translations/r67_14y_approved_lock.json'
Y=ROOT/'local/r67-14y-event-lifecycle-inspection-save.elf'


def verify_frozen_y(raw:bytes,lock:dict)->dict:
    if lock["schema_version"]!=1 or lock["approval_status"]!="USER_VISUALLY_APPROVED_2026_10_12":
        raise ValueError("Unapproved or invalid y UI lock")
    if hashlib.sha256(raw).hexdigest()!=lock["staged_elf_sha256"]:
        raise ValueError("Previously user-approved y executable differs in any byte")
    q=verify_approved(raw,json.loads(Q.read_text()))
    t=verify_ui(raw,json.loads(T.read_text()))
    validate_y_inspections(raw)
    verify_save_identity(raw)
    assert_all_tablets_fit(raw)
    return dict(status="PASS_ALL_APPROVED_Y_EXECUTABLE_BYTES",
                protected_q=q["status"],protected_t=t["status"],
                exact_elf_sha256=lock["staged_elf_sha256"])

def verify_new_diagnostic_scope(
    approved:bytes,candidate:bytes,lock:dict,allowed_pointer_offsets:tuple[int,...]
)->dict:
    verify_frozen_y(approved,lock)
    requested={int(raw,16) for raw in lock["z_exception_review"]["scope"]}
    if requested!=set(allowed_pointer_offsets):
        raise ValueError("Proposed scoped exception differs from exact user-requested two fixes")
    if lock["z_exception_review"]["new_candidate_gameplay_approval"]!="PENDING":
        raise ValueError("Unexpected visual-approval state; review explicit user evidence")
    if len(candidate)<len(approved):
        raise ValueError("Truncated approved ELF")
    allowed=set(range(0x64,0x68))
    for ptr in requested:allowed.update(range(ptr,ptr+4))
    modified={i for i,(a,b) in enumerate(zip(approved,candidate)) if a!=b}
    if not modified or modified-allowed:
        raise ValueError(f"An approved r67.14y code/data byte changed outside explicit scope: {modified-allowed}")
    old_size=struct.unpack_from("<I",approved,0x64)[0]
    new_size=struct.unpack_from("<I",candidate,0x64)[0]
    if new_size!=len(candidate)-0x803150 or new_size<old_size:
        raise ValueError("Inconsistent append-only translation segment")
    q=verify_approved(candidate,json.loads(Q.read_text()))
    t=verify_ui(candidate,json.loads(T.read_text()))
    validate_y_inspections(candidate)
    verify_save_identity(candidate)
    assert_all_tablets_fit(candidate)
    return dict(status="PASS_EXACT_FIVE_REQUESTED_POINTER_OWNERS_ONLY",
                original_approved_y_elf_unchanged=True,
                changed_prior_elf_bytes=len(modified),
                permitted_existing_pointer_offsets=list(map(hex,sorted(requested))),
                appended_bytes=len(candidate)-len(approved),
                previous_ui_owners_verified=True,
                q=q["status"],t=t["status"],gameplay_approved=False)

def require_dual_approval(approval:dict)->None:
    """Promotion gate: no guessed, blank or pending signoffs for a new change."""
    for field in ("explicit_user_visual_approval","documented_ai_technical_review"):
        evidence=approval.get(field)
        if not isinstance(evidence,str) or evidence.strip().lower() in ("","pending","yes","true"):
            raise ValueError(f"Explicit, attributable review evidence missing: {field}")
    if approval.get("release_status")!="APPROVED_FOR_MAIN":
        raise ValueError("Diagnostic release has not been approved for promotion")
