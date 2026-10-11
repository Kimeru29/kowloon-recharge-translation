"""r67.14e: Chamber of Lions glyph X scale at a safe pre-layout hook.

r67.14d's cloned renderer was rejected by the user: corrupted text,
oversized bluish backing, and shortened timer. This variant never clones
native code or intercepts the font constructor. It retains the successful
r67.14c comment text/Y positioning and the two original background layers.

A strictly scoped saved-register marker is set only while processing one
of three official old-man comment lines. The original renderer's empty-font
glyph-clear call (0x189ED8) is intercepted, calls the ORIGINAL glyph-clear,
and adjusts the new font's xScale BEFORE the subsequent glyph-advance
calculations. No timing counters, backing sprites or shared constructor touched.
User runtime visual acceptance required before release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.r67_chamber_story_text_only import (
    APPROVED_SHA256, APPROVED_POINTERS, SCRIPT_POINTER_OFFSETS,
    STORY_CALLS, ORIGINAL_RENDERER_VA, ORIGINAL_JAL, ELF_BIAS,
    ELF_SEGMENT_FO, ELF_SEGMENT_VA, ELF_SEGMENT_RESERVE,
    SHORT_MESSAGE_X, HORIZONTAL_SCALE, Assembly, _i, _r, _float_word, _jal,
)

PRE_GLYPH_CALL_SITE = 0x189ED8
PRE_GLYPH_ORIGINAL_CALLEE = 0x188940
CALL_SITE_PREIMAGE = _jal(PRE_GLYPH_ORIGINAL_CALLEE)
FONT_OBJ_XSCALE_OFFSET = 0x48
COMMENT_ONLY_MARKER = 0x4C494F4E  # 'LION'; held transiently in callee-saved s7
MARKER_REGISTER = 23

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _bytes(words:list[int])->bytes:
    return struct.pack("<"+"I"*len(words),*words)

def comment_text_helper(y:float)->bytes:
    """Precisely the accepted 14c helper plus a temporary saved s7 marker."""
    m=Assembly()
    m.emit(_i(9,29,29,-0x20))       # sp -= 32
    m.emit(_i(43,29,31,0))         # save ra
    m.emit(_i(43,29,8,4))          # save t0
    m.emit(_i(43,29,9,8))          # save t1
    m.emit(_i(43,29,0,12))         # clear boolean matched flag
    m.emit(_i(43,29,23,16))        # save caller s7, MIPS callee-saved
    for ptr in APPROVED_POINTERS:
        m.const(8,ptr)
        m.branch(4,9,8,"matched")
        m.emit(0)
    m.branch(4,0,0,"render")
    m.emit(0)
    m.label("matched")
    m.const(23,COMMENT_ONLY_MARKER) # scope the nested native font clear
    m.const(8,_float_word(y))
    m.emit((17<<26)|(4<<21)|(8<<16)|(13<<11))  # mtc1 t0,f13
    m.const(8,1)
    m.emit(_i(43,29,8,12))
    m.emit(_i(35,29,8,8))
    m.const(9,APPROVED_POINTERS[-1])
    m.branch(5,8,9,"render")
    m.emit(0)
    m.const(8,_float_word(SHORT_MESSAGE_X))
    m.emit((17<<26)|(4<<21)|(8<<16)|(12<<11))  # mtc1 t0,f12
    m.label("render")
    m.emit(_i(35,29,9,8))          # original t1 before native renderer
    m.emit(_jal(ORIGINAL_RENDERER_VA))
    m.emit(0)
    m.emit(_i(35,29,8,12))         # matched flag
    m.branch(4,8,0,"done")
    m.emit(0)
    m.branch(4,2,0,"done")         # null native return?
    m.emit(0)
    m.emit(_i(35,2,8,0x3c))       # lw t0,0x3c(v0)
    m.branch(4,8,0,"done")
    m.emit(0)
    m.const(9,_float_word(HORIZONTAL_SCALE))
    m.emit(_i(43,8,9,FONT_OBJ_XSCALE_OFFSET))  # retain 14c postscale
    m.label("done")
    m.emit(_i(35,29,23,16))       # restore original caller s7
    m.emit(_i(35,29,9,8))
    m.emit(_i(35,29,8,4))
    m.emit(_i(35,29,31,0))
    m.emit(_i(9,29,29,0x20))
    m.emit(_r(31,0,0,0,8))
    m.emit(0)
    return m.done()

def pre_glyph_font_clear_helper()->bytes:
    """Calls exact original glyph clear, then shrinks only marked font xScale.

    Intercepts JAL 0x188940 at native 0x189ED8 (existing next word is NOP).
    On entry native renderer s2 is the newly constructed font object; original
    glyph clear removes old text nodes. The subsequent native text-layout
    function has not yet been called. No cloned code or ctor stack arguments.
    """
    m=Assembly()
    m.emit(_i(9,29,29,-0x20))       # sp -=32
    m.emit(_i(43,29,31,0))         # original return
    m.emit(_i(43,29,8,4))          # preserve caller t0
    m.emit(_i(43,29,9,8))          # preserve caller t1
    m.emit(_jal(PRE_GLYPH_ORIGINAL_CALLEE))
    m.emit(0)
    m.const(8,COMMENT_ONLY_MARKER)
    m.branch(5,23,8,"done")        # bne s7,t0,done
    m.emit(0)
    m.branch(4,18,0,"done")        # beq s2,zero,done
    m.emit(0)
    m.const(9,_float_word(HORIZONTAL_SCALE))
    m.emit(_i(43,18,9,FONT_OBJ_XSCALE_OFFSET)) # sw t1,+0x48(s2)
    m.label("done")
    m.emit(_i(35,29,9,8))
    m.emit(_i(35,29,8,4))
    m.emit(_i(35,29,31,0))
    m.emit(_i(9,29,29,0x20))
    m.emit(_r(31,0,0,0,8))
    m.emit(0)
    return m.done()

def apply(source:bytes)->tuple[bytes,dict]:
    if sha(source)!=APPROVED_SHA256:
        raise ValueError("Refusing non-approved r67.12 ELF")
    for off,ptr in zip(SCRIPT_POINTER_OFFSETS,APPROVED_POINTERS,strict=True):
        if struct.unpack_from("<I",source,off)[0]!=ptr:
            raise ValueError("Chamber comment pointer preimage drift")
    fo,va,size,reserve,flags=(
        struct.unpack_from("<I",source,k)[0] for k in (0x58,0x5c,0x64,0x68,0x6c)
    )
    if (fo,va,fo+size,reserve,flags)!=(
        ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(source),ELF_SEGMENT_RESERVE,7
    ):raise ValueError("Reserved translation segment preimage changed")
    sites=[site for site,_ in STORY_CALLS]+[PRE_GLYPH_CALL_SITE]
    expected=[ORIGINAL_JAL]*len(STORY_CALLS)+[CALL_SITE_PREIMAGE]
    for site,word in zip(sites,expected,strict=True):
        off=site-ELF_BIAS
        if struct.unpack_from("<2I",source,off)!=(word,0):
            raise ValueError(f"Original native callsite preimage drift at {site:#x}")

    patch=bytearray(source)
    while len(patch)&3:patch.append(0)
    helpers=[]
    def append(payload:bytes)->int:
        target=va+len(patch)-fo
        if target&3 or target>=0x10000000:raise ValueError("JAL target unreachable")
        if len(patch)+len(payload)-fo>reserve:raise ValueError("Segment exceeds reserved memory")
        patch.extend(payload)
        return target

    pre_glyph=append(pre_glyph_font_clear_helper())
    struct.pack_into("<I",patch,PRE_GLYPH_CALL_SITE-ELF_BIAS,_jal(pre_glyph))
    for site,y in STORY_CALLS:
        data=comment_text_helper(y)
        target=append(data)
        struct.pack_into("<I",patch,site-ELF_BIAS,_jal(target))
        helpers.append(dict(site=hex(site),helper_va=hex(target),bytes=len(data)))
    struct.pack_into("<I",patch,0x64,len(patch)-fo)
    allowed=set(range(0x64,0x68))
    for site in sites:
        allowed.update(range(site-ELF_BIAS,site-ELF_BIAS+4))
    changed=[i for i,(a,b) in enumerate(zip(source,patch)) if a!=b]
    if not changed or any(i not in allowed for i in changed):
        raise ValueError("Unexpected unrelated original byte mutation")
    for saved_identity in (b"SLPM-66511",b"BISLPM-66511Save"):
        if saved_identity not in patch:raise ValueError("Save namespace changed")
    meta=dict(
        status="DIAGNOSTIC_ONLY_NEEDS_FRESH_CHAMBER_RUNTIME_CAPTURE",
        revision="r67.14e",
        approved_baseline_sha=APPROVED_SHA256,
        new_staged_elf_sha=sha(patch),
        marker_hex=hex(COMMENT_ONLY_MARKER),
        marker_register="s7_saved_restored_per_story_call",
        native_renderer_untouched=True,
        native_ctor_untouched=True,
        original_clear_function_untouched=True,
        intercepted_native_callee_va=hex(PRE_GLYPH_ORIGINAL_CALLEE),
        text_y_anchors=list(y for _,y in STORY_CALLS),
        font_x_scale=HORIZONTAL_SCALE,
        pre_glyph_helper_va=hex(pre_glyph),
        story_helpers=helpers,
        original_bytes_changed=list(map(hex,changed)),
        blue_green_panel_and_timing_unchanged=True,
        approved_history_hant_untouched=True,
        runtime_verified=False,
        release_approved=False
    )
    return bytes(patch),meta

def main()->None:
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ("baseline","output","report"):
        ap.add_argument("--"+key,required=True,type=Path)
    args=ap.parse_args()
    if args.output.exists() or args.report.exists():raise FileExistsError("No overwrite")
    elf,meta=apply(args.baseline.read_bytes())
    args.output.write_bytes(elf)
    args.report.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    print(json.dumps(meta,sort_keys=True))

if __name__=="__main__":
    main()
