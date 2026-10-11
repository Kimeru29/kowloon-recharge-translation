"""r67.14l: Restore the original companion EVENT second-line index.

The H_TalkBuddyTask first event-row renderer returns a live text-object
pointer in v0. At 0x1661c4 the caller already stores that pointer at
task+0x28, but the original unconditional jump from 0x1661c8 targets
0x166208, storing v0 *again* and falling into "sll a1,v0,4", incorrectly
treating a pointer as the row index. The native first-row source lookup at
0x166138 proves the intended subindex is lh v0,0x0A(s0).

Patch only original-event continuation:
  0x1661c8: b 0x16620c  (skip unnecessary second object-pointer store)
  0x1661cc: lh v0,0xa(s0) (MIPS branch delay slot; recover row subindex)
Then native 0x16620c "sll a1,v0,4" indexes the +0x0C second text pointer
of the correct 0x80-stride event row. Second source nulls remain null.
The AFK path at 0x1661d0..0x166208 and its call to specialized
0x1950A0 remain byte-identical and consume their unchanged continuation.
No font, bubble, glyph X/Y, text, timing, history or sprite bytes modified.

r67.14k is the source; do not reapply rejected j's glyph-node mutation.
Runtime acceptance required before release.
"""
from __future__ import annotations
import argparse,struct,json
from pathlib import Path
from tools.r67_chamber_pre_glyph_font_target import sha
from tools.r67_chamber_story_text_only import _i,ELF_BIAS

EXPECTED_K_SHA = "5c0afd910bba0bf8f66338ae8589c4437492d68116c22dfea5864e167b0ba7e2"
EVENT_BRANCH_VA=0x1661C8
EVENT_DELAY_VA=0x1661CC
FIRST_ROW_STORE_VA=0x1661C4
AFK_SECOND_ROW_STORE_VA=0x166208
NATIVE_NEXT_ROW_SLL_VA=0x16620C
NATIVE_FIRST_ROW_INDEX_LOAD_VA=0x166138
EVENT_BRANCH_ORIGINAL=_i(4,0,0,15)  # beq $zero,$zero,0x166208
EVENT_BRANCH_NEW=_i(4,0,0,16)       # beq $zero,$zero,0x16620c
EVENT_DELAY_ORIGINAL=0
EVENT_DELAY_NEW=_i(33,16,2,10)    # lh v0,0xa(s0)
FIRST_ROW_STORE=_i(43,16,2,0x28)  # sw v0,0x28(s0)
NEXT_ROW_SHIFT=(2<<16)|(5<<11)|(4<<6) # sll a1,v0,4
EXPECTED_FIRST_INDEX_LOAD=EVENT_DELAY_NEW

def apply(source:bytes)->tuple[bytes,dict]:
    if sha(source)!=EXPECTED_K_SHA:
        raise ValueError("Refusing source other than exact r67.14k ELF")
    before=bytes(source)
    changed=bytearray(source)
    def off(va:int)->int:return va-ELF_BIAS
    expected={
        FIRST_ROW_STORE_VA:FIRST_ROW_STORE,
        EVENT_BRANCH_VA:EVENT_BRANCH_ORIGINAL,
        EVENT_DELAY_VA:EVENT_DELAY_ORIGINAL,
        AFK_SECOND_ROW_STORE_VA:FIRST_ROW_STORE,
        NATIVE_NEXT_ROW_SLL_VA:NEXT_ROW_SHIFT,
        NATIVE_FIRST_ROW_INDEX_LOAD_VA:EXPECTED_FIRST_INDEX_LOAD,
    }
    for va,word in expected.items():
        current=struct.unpack_from('<I',before,off(va))[0]
        if current!=word:raise ValueError(f"Callflow preimage drift at {va:#x}: got {current:#x} expected {word:#x}")
    struct.pack_into('<I',changed,off(EVENT_BRANCH_VA),EVENT_BRANCH_NEW)
    struct.pack_into('<I',changed,off(EVENT_DELAY_VA),EVENT_DELAY_NEW)
    modified=[i for i,(a,b) in enumerate(zip(before,changed)) if a!=b]
    allowed={off(va)+i for va in (EVENT_BRANCH_VA,EVENT_DELAY_VA) for i in range(4)}
    if not modified or set(modified)-allowed or len(changed)!=len(before):
        raise ValueError("Unexpected executable modification beyond two instructions")
    return bytes(changed),{
        "revision":"r67.14l",
        "status":"DIAGNOSTIC_AWAITING_MANUAL_VISUAL_ACCEPTANCE",
        "source_14k_sha256":sha(before),
        "output_elf_sha256":sha(changed),
        "modified_bytes":len(modified),
        "modified_file_offsets":[hex(i) for i in modified],
        "changed_branch":{"va":hex(EVENT_BRANCH_VA),"old":hex(EVENT_BRANCH_ORIGINAL),"new":hex(EVENT_BRANCH_NEW)},
        "changed_delay_slot":{"va":hex(EVENT_DELAY_VA),"old":hex(EVENT_DELAY_ORIGINAL),"new":hex(EVENT_DELAY_NEW)},
        "original_first_text_owner_saved_before_jump":True,
        "native_index_loaded_before_second_line_lookup":True,
        "afk_second_line_constructor_and_continuation_byte_identical":True,
        "preserve_event_generic_font_scale":True,
        "preserve_afk_geometry_and_translation":True,
        "runtime_verified":False,"release_approved":False
    }
def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("input","output","report"):p.add_argument("--"+arg,required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():
        raise FileExistsError("Refusing to overwrite diagnostic artifact")
    out,j=apply(a.input.read_bytes())
    a.output.write_bytes(out);a.report.write_text(json.dumps(j,sort_keys=True,indent=2)+"\n")
    print(json.dumps(j,sort_keys=True))
if __name__=="__main__":main()
