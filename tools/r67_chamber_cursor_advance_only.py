"""r67.14h diagnostic: compress ONLY matched story-comment horizontal cursor advance.

The r67.14g early font +0x48 mutation is REJECTED: live screenshot places
text below the approved bubble. Unlike that patch, this module never writes
font state before glyph construction. It replaces only the native horizontal
cursor-step load at 0x18E004, preserving its original 0x18E008 delay slot,
then conditionally scales the temporary f1 cursor-advance operand. The native
vertical-step path at 0x18E024 is untouched. Comment wrappers preserve the
approved r67.14e Y positions, text, post-render glyph width, and short X.

NOT APPROVED without an actual fresh-entry PCSX2 screenshot.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from tools.r67_chamber_story_text_only import (
    APPROVED_SHA256, APPROVED_POINTERS, SCRIPT_POINTER_OFFSETS,
    STORY_CALLS, ORIGINAL_JAL, ELF_BIAS, ELF_SEGMENT_FO,
    ELF_SEGMENT_VA, ELF_SEGMENT_RESERVE, HORIZONTAL_SCALE,
    Assembly, _i, _jal, _float_word,
)
from tools.r67_chamber_pre_glyph_font_target import (
    COMMENT_ONLY_MARKER, comment_text_helper, sha,
)

CURSOR_STEP_SITE = 0x18E004
CURSOR_ORIGINAL_WORD = 0xC6810048  # lwc1 f1,+0x48(s4) in horizontal-only path
CURSOR_DELAY_SLOT = 0x44800000    # mtc1 zero,f0; must remain unchanged
VERTICAL_STEP_SITE = 0x18E024
HORIZONTAL_ADVANCE_MULTIPLIER = 0.55


def cursor_step_helper() -> bytes:
    """Preserve native registers/FPRs and adjust only the local X-step operand.

    The original native instruction loads f1 from font+0x48. Horizontal
    advance later consumes f1 at 0x18E014 and advances f21 at 0x18E018.
    We multiply f1, NOT the persistent font property or glyph coordinates.
    Original 0x18E008 executes in the replacement JAL delay slot.
    """
    a = Assembly()
    a.emit(_i(9,29,29,-0x10))   # addiu sp,sp,-16 (aligned)
    a.emit(_i(43,29,8,0))       # sw t0,0(sp)
    a.emit(_i(57,29,2,4))       # swc1 f2,4(sp)
    a.emit(CURSOR_ORIGINAL_WORD) # lwc1 f1,+0x48(s4): original native operation
    a.const(8, COMMENT_ONLY_MARKER)
    a.branch(5,23,8,"done")     # bne s7,t0,done: only marked comment
    a.emit(0)
    a.const(8,_float_word(HORIZONTAL_ADVANCE_MULTIPLIER))
    a.emit((17<<26)|(4<<21)|(8<<16)|(2<<11))  # mtc1 t0,f2
    a.emit((17<<26)|(16<<21)|(2<<16)|(1<<11)|(1<<6)|2) # mul.s f1,f1,f2
    a.label("done")
    a.emit(_i(49,29,2,4))       # lwc1 f2,4(sp), preserve live FPR
    a.emit(_i(35,29,8,0))       # lw t0,0(sp), preserve live GPR
    a.emit(_i(9,29,29,0x10))
    a.emit(0x03E00008)          # jr ra
    a.emit(0)
    return a.done()


def apply(source:bytes)->tuple[bytes,dict]:
    if sha(source)!=APPROVED_SHA256:
        raise ValueError("Refusing non-approved r67.12 ELF")
    for off,ptr in zip(SCRIPT_POINTER_OFFSETS,APPROVED_POINTERS,strict=True):
        if struct.unpack_from("<I",source,off)[0]!=ptr:
            raise ValueError("Chamber comment original pointers drifted")
    fo,va,size,reserve,flags=(
        struct.unpack_from("<I",source,k)[0] for k in (0x58,0x5c,0x64,0x68,0x6c)
    )
    if (fo,va,fo+size,reserve,flags)!=(
        ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(source),ELF_SEGMENT_RESERVE,7
    ):
        raise ValueError("Approved translation segment changed")
    for site,word in [(CURSOR_STEP_SITE,CURSOR_ORIGINAL_WORD)]+[
        (site,ORIGINAL_JAL) for site,_ in STORY_CALLS
    ]:
        if struct.unpack_from('<I',source,site-ELF_BIAS)[0]!=word:
            raise ValueError(f'Original native preimage drift at {site:#x}')
    if struct.unpack_from('<I',source,CURSOR_STEP_SITE-ELF_BIAS+4)[0]!=CURSOR_DELAY_SLOT:
        raise ValueError('Original horizontal JAL delay slot changed')
    p=bytearray(source)
    while len(p)&3:p.append(0)
    def append(blob:bytes)->int:
        dest=va+len(p)-fo
        if dest&3 or dest>=0x10000000 or len(p)+len(blob)-fo>reserve:
            raise ValueError('Native helper unreachable or segment overflow')
        p.extend(blob)
        return dest
    cursor=append(cursor_step_helper())
    struct.pack_into('<I',p,CURSOR_STEP_SITE-ELF_BIAS,_jal(cursor))
    wrappers=[]
    for site,y in STORY_CALLS:
        helper_va=append(comment_text_helper(y))
        struct.pack_into('<I',p,site-ELF_BIAS,_jal(helper_va))
        wrappers.append(dict(call_site=hex(site),helper_va=hex(helper_va),y=y))
    struct.pack_into('<I',p,0x64,len(p)-fo)
    sites=[CURSOR_STEP_SITE]+[site for site,_ in STORY_CALLS]
    allowed=set(range(0x64,0x68))
    for site in sites:allowed.update(range(site-ELF_BIAS,site-ELF_BIAS+4))
    changed=[i for i,(a,b) in enumerate(zip(source,p)) if a!=b]
    if not changed or any(i not in allowed for i in changed):
        raise ValueError('Unexpected unrelated original ELF mutation')
    for name in (b'SLPM-66511',b'BISLPM-66511Save'):
        if name not in p: raise ValueError('Game save identity missing')
    return bytes(p),dict(
        revision='r67.14h',status='DIAGNOSTIC_REQUIRES_FRESH_CHAMBER_VISUAL_REVIEW',
        baseline_sha256=APPROVED_SHA256,staged_elf_sha256=sha(p),
        native_horizontal_cursor_site=hex(CURSOR_STEP_SITE),
        cursor_helper_va=hex(cursor),cursor_multiplier=HORIZONTAL_ADVANCE_MULTIPLIER,
        vertical_advance_site=hex(VERTICAL_STEP_SITE),
        matched_source_pointers=[hex(x) for x in APPROVED_POINTERS],
        approved_story_wrappers=wrappers,approved_post_glyph_xscale=HORIZONTAL_SCALE,
        original_unchanged_callsite_delays=True,
        original_font_constructor_untouched=True,
        original_glyph_clear_untouched=True,
        original_vertical_path_untouched=True,
        font_state_unchanged_before_glyph_creation=True,
        background_and_timer_unchanged=True,
        previous_history_and_hant_untouched=True,
        mutated_existing_bytes=[hex(i) for i in changed],
        runtime_verified=False,release_approved=False,
    )


def main()->None:
    a=argparse.ArgumentParser(description=__doc__)
    for flag in ('baseline','output','report'):
        a.add_argument('--'+flag,required=True,type=Path)
    args=a.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError('Never overwrite previous diagnostic artifacts')
    payload,report=apply(args.baseline.read_bytes())
    args.output.write_bytes(payload)
    args.report.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps(report,sort_keys=True))

if __name__=='__main__':main()
