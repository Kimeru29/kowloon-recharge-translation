"""Experimental r67 START history: chronological speaker/body sections.

Retain horizontal glyph direction and history-only X/Y row mapping from r67.10.
The native history viewer traverses log records newest-to-oldest. A tiny helper
instead maps its visible row ordinal into chronological circular-buffer slots,
without changing any other global history reader. The original gap belongs
after spoken dialogue (tag==0), not after Japanese speaker columns.
Not a release: >12-record paging/scroll is not fully validated yet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

BASE_SHA = "572022168275e32b3fba3ba2373eb7a6f6521631574ba27106f870929b01ca3a"
VA_MINUS_OFFSET = 0xFFF80
INDEX_CALLSITE = 0x253AE8
SPACER_BRANCH_VA = 0x253D3C
SPACER_SKIP_VA = 0x253D48
PREIMAGES = {
    INDEX_CALLSITE - VA_MINUS_OFFSET: 0x00131080,      # sll v0,s3,2
    INDEX_CALLSITE + 4 - VA_MINUS_OFFSET: 0x00531021,  # addu v0,v0,s3
    SPACER_BRANCH_VA - VA_MINUS_OFFSET: 0x14400004,    # bnez v0, extra
    SPACER_SKIP_VA - VA_MINUS_OFFSET: 0x14430007,      # bne v0,v1, after
}
REPLACEMENTS = {
    SPACER_BRANCH_VA - VA_MINUS_OFFSET: 0x10400004,    # beqz type,extra: spoken text
    SPACER_SKIP_VA - VA_MINUS_OFFSET: 0x10000007,      # b after: no gap after label
}
RING_CAPACITY = 255
MAX_VISIBLE = 12

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def chronological_slots(count: int, visible: int) -> tuple[int, ...]:
    """Model of the MIPS helper for the visible page (supports ring rollover)."""
    if count < visible or visible < 1 or visible > MAX_VISIBLE:
        raise ValueError("Invalid count/visible window")
    return tuple((count - visible + ordinal) % RING_CAPACITY
                 for ordinal in range(visible))

def _i(opcode: int, rs: int, rt: int, immediate: int) -> int:
    if not -32768 <= immediate <= 65535:
        raise ValueError("MIPS immediate overflow")
    return ((opcode & 0x3F) << 26) | (rs << 21) | (rt << 16) | (immediate & 0xFFFF)

def _r(rs: int, rt: int, rd: int, sa: int, funct: int) -> int:
    return (rs << 21) | (rt << 16) | (rd << 11) | (sa << 6) | funct

def _jal(target: int) -> int:
    if target & 3:
        raise ValueError("Misaligned native history helper")
    return 0x0C000000 | ((target >> 2) & 0x03FFFFFF)

def helper() -> bytes:
    words = (
        _i(0x23, 28, 2, -0x1DAC), # lw v0,-0x1dac(gp): shared history global
        _i(0x21,  2, 2, 0x30FC), # lh v0,0x30fc(v0): story-record count
        _i(0x21, 17, 3, 0x007A), # lh v1,0x7a(s1): visible count 1..12
        _r(2, 3, 2, 0, 0x23),    # subu v0,v0,v1: oldest visible ordinal
        _r(2, 18, 2, 0, 0x21),   # addu v0,v0,s2: advance in story order
        _i(0x09, 0, 3, RING_CAPACITY), # addiu v1,zero,255
        _r(2, 3, 0, 0, 0x1A),    # div v0,v1
        _r(0, 0, 2, 0, 0x10),    # mfhi v0
        _r(0, 2, 3, 2, 0),       # sll v1,v0,2
        _r(3, 2, 2, 0, 0x21),    # addu v0,v1,v0 (5*slot)
        _r(31, 0, 0, 0, 0x08),   # jr ra
        0,                      # nop
    )
    return b"".join(struct.pack("<I", word) for word in words)

def apply(baseline: bytes) -> tuple[bytes,dict]:
    if sha(baseline) != BASE_SHA:
        raise ValueError("r67.10 baseline SHA drift")
    fo,va,size,reserve,flags = (struct.unpack_from("<I",baseline,p)[0]
                                 for p in (0x58,0x5C,0x64,0x68,0x6C))
    if (fo,va,fo+size,reserve,flags)!=(0x803150,0x902F00,len(baseline),0x100000,7):
        raise ValueError("r67 ELF translation segment drift")
    for pos,expected in PREIMAGES.items():
        if struct.unpack_from("<I",baseline,pos)[0]!=expected:
            raise ValueError(f"history-local preimage mismatch: {pos:#x}")
    patched=bytearray(baseline)
    while len(patched)&3:
        patched.append(0)
    target=va+len(patched)-fo
    if (INDEX_CALLSITE>>28)!=(target>>28) or target&3:
        raise ValueError("History branch cannot reach helper")
    shim=helper()
    patched.extend(shim)
    if len(patched)-fo>reserve:
        raise ValueError("Insufficient PT_LOAD reserve")
    struct.pack_into("<I",patched,INDEX_CALLSITE-VA_MINUS_OFFSET,_jal(target))
    struct.pack_into("<I",patched,INDEX_CALLSITE+4-VA_MINUS_OFFSET,0)
    for pos,new in REPLACEMENTS.items():
        struct.pack_into("<I",patched,pos,new)
    struct.pack_into("<I",patched,0x64,len(patched)-fo)
    allowed=set(range(0x64,0x68))
    for at in PREIMAGES:
        allowed.update(range(at,at+4))
    modified=[i for i,(a,b) in enumerate(zip(baseline,patched)) if a!=b]
    if set(modified)-allowed:
        raise ValueError("Unrelated original executable byte changed")
    for identity in (b"SLPM-66511",b"BISLPM-66511Save"):
        if identity not in patched:
            raise ValueError("Save identity unexpectedly absent")
    return bytes(patched),{
        "status":"DIAGNOSTIC_ONLY_PENDING_VISUAL_AND_SCROLL_CHECK",
        "input_sha256":BASE_SHA,
        "output_sha256":sha(patched),
        "history_index_callsite":hex(INDEX_CALLSITE),
        "history_index_helper_va":hex(target),
        "helper_bytes":len(shim),
        "max_initial_visible_records":MAX_VISIBLE,
        "story_order":"oldest-to-newest within visible circular-buffer page",
        "gap_after":"spoken content, type byte == 0",
        "changed_existing_offsets":[hex(x) for x in modified],
        "horizontal_direction_preserved":True,
        "normal_dialogue_untouched":True,
        "protected_basic_attack_untouched":True,
        "save_identifiers_unchanged":True,
        "full_history_paging_verified":False,
        "release_approved":False,
    }

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("Refusing to overwrite diagnostic")
    new,report=apply(args.baseline.read_bytes())
    args.output.write_bytes(new)
    args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":
    main()
