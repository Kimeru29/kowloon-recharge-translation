"""r67.14d Chamber of Lions: apply font X scale BEFORE native glyph layout.

Preserves approved r67.14c green speech bubble, bluish backing, anchors, sentence
content, history, and H.A.N.T. Only three exact story-comment text pointers are
eligible. For those only, calls a byte-identical PRIVATE clone of native
0x189E40 whose single constructor-call JAL invokes a wrapper that sets the font
X scale on the new object BEFORE glyphs are positioned. Nonmatching story
comments continue calling the original native renderer unchanged.

This fixes the architectural bug in r67.14b/c, which applied +0x48 X scale to
the font object AFTER native renderer 0x189E40 had already built glyph spacing.
No sprite path, global font constructor, glyph rasterizer or dialog corpus is
changed. Runtime visual acceptance still required before release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.r67_chamber_story_text_only import (
    APPROVED_SHA256, APPROVED_POINTERS, SCRIPT_POINTER_OFFSETS, STORY_CALLS,
    ORIGINAL_RENDERER_VA, ORIGINAL_JAL, ELF_BIAS, ELF_SEGMENT_FO,
    ELF_SEGMENT_VA, ELF_SEGMENT_RESERVE, SHORT_MESSAGE_X, HORIZONTAL_SCALE,
    Assembly, _float_word, _i, _r, _jal,
)

CLONE_SOURCE_VA = ORIGINAL_RENDERER_VA
CLONE_END_VA = 0x18A080
FONT_CTOR_VA = 0x188AD0
CTOR_JAL_VA = 0x189EAC
CTOR_JAL_ORIGINAL = _jal(FONT_CTOR_VA)
FONT_SCALE_OFFSET = 0x48
HELPER_VERSION = "r67.14d-pre-glyph-advance"

def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _check_relocatable_native_function(baseline:bytes)->bytes:
    """All PC-relative branches stay inside source; JAL absolute addresses stay valid."""
    start=CLONE_SOURCE_VA-ELF_BIAS
    end=CLONE_END_VA-ELF_BIAS
    code=baseline[start:end]
    if len(code)!=576:raise ValueError("Unexpected native function size")
    seen_ctor=[]
    for index in range(0,len(code),4):
        va=CLONE_SOURCE_VA+index
        w=struct.unpack_from("<I",code,index)[0]
        op,rs,rt=w>>26,(w>>21)&31,(w>>16)&31
        if w==CTOR_JAL_ORIGINAL:
            seen_ctor.append(index)
        is_branch=(
            op in (4,5,6,7,20,21,22,23)
            or (op==1 and rt in (0,1,2,3,16,17,18,19))
            or (op==17 and rs==8)
        )
        if is_branch:
            imm=struct.unpack("<h",struct.pack("<H",w&0xffff))[0]
            target=va+4+4*imm
            if not CLONE_SOURCE_VA<=target<=CLONE_END_VA:
                raise ValueError(f"Native clone has external relative branch {va:#x}->{target:#x}")
        # All jumps must remain in the same high-VA segment after relocation.
        if op in (2,3):
            target=((va+4)&0xf0000000)|((w&0x3ffffff)<<2)
            if target>=0x10000000:raise ValueError("Native clone absolute call crosses segment")
    if seen_ctor!=[CTOR_JAL_VA-CLONE_SOURCE_VA]:
        raise ValueError(f"Unexpected ctor jal owners {seen_ctor}")
    if struct.unpack_from("<I",code,CTOR_JAL_VA-CLONE_SOURCE_VA+4)[0]:
        raise ValueError("Original ctor delay slot is not NOP")
    if struct.unpack_from("<2I",code,len(code)-8)!=(0x03e00008,0):
        raise ValueError("Native function return epilogue drift")
    return code

def make_pre_layout_constructor()->bytes:
    """Call original font ctor; set only its X scale before any glyph is created."""
    m=Assembly()
    # The original constructor reads three stack arguments at caller SP+0,
    # +8 and +16 (f0.5 clip/color parameters). Preserve those arguments by
    # forwarding them from the uncloned native caller's frame before JAL.
    m.emit(_i(9,29,29,-0x40))       # addiu sp,sp,-64
    m.emit(_i(43,29,31,0x20))      # save ra out of outgoing-argument area
    for caller_slot in (0,8,16):
        m.emit(_i(35,29,8,0x40+caller_slot))   # lw t0,old SP+slot
        m.emit(_i(43,29,8,caller_slot))        # sw t0,new SP+slot
    m.emit(_jal(FONT_CTOR_VA))
    m.emit(0)
    m.branch(4,2,0,"done")         # font ctor returned NULL: do not dereference
    m.emit(0)
    m.const(8,_float_word(HORIZONTAL_SCALE))
    m.emit(_i(43,2,8,FONT_SCALE_OFFSET)) # sw t0,0x48(v0) prior to layout
    m.label("done")
    m.emit(_i(35,29,31,0x20))
    m.emit(_i(9,29,29,0x40))
    m.emit(_r(31,0,0,0,8))
    m.emit(0)
    return m.done()

def make_story_dispatch(text_y:float,clone_va:int)->bytes:
    """Original story pointer filter, now choosing cloned prelayout or original."""
    m=Assembly()
    m.emit(_i(9,29,29,-0x20))
    m.emit(_i(43,29,31,0))
    m.emit(_i(43,29,8,4))
    m.emit(_i(43,29,9,8))
    m.emit(_i(43,29,0,12)) # match flag
    for ptr in APPROVED_POINTERS:
        m.const(8,ptr)
        m.branch(4,9,8,"matched")
        m.emit(0)
    m.branch(4,0,0,"dispatch")
    m.emit(0)
    m.label("matched")
    m.const(8,_float_word(text_y))
    m.emit((17<<26)|(4<<21)|(8<<16)|(13<<11)) # mtc1 t0,f13
    m.const(8,1)
    m.emit(_i(43,29,8,12))
    m.emit(_i(35,29,8,8))
    m.const(9,APPROVED_POINTERS[-1])
    m.branch(5,8,9,"dispatch")
    m.emit(0)
    m.const(8,_float_word(SHORT_MESSAGE_X))
    m.emit((17<<26)|(4<<21)|(8<<16)|(12<<11)) # mtc1 t0,f12
    m.label("dispatch")
    m.emit(_i(35,29,9,8))        # native renderer expects original t1
    m.emit(_i(35,29,8,12))       # matched flag
    m.branch(4,8,0,"original")
    m.emit(0)
    m.emit(_jal(clone_va))       # matched: the cloned function with prelayout scale
    m.emit(0)
    m.branch(4,0,0,"return")
    m.emit(0)
    m.label("original")
    m.emit(_jal(ORIGINAL_RENDERER_VA)) # all other comments unchanged
    m.emit(0)
    m.label("return")
    m.emit(_i(35,29,9,8))
    m.emit(_i(35,29,8,4))
    m.emit(_i(35,29,31,0))
    m.emit(_i(9,29,29,0x20))
    m.emit(_r(31,0,0,0,8))
    m.emit(0)
    return m.done()

def apply(baseline:bytes)->tuple[bytes,dict]:
    if _sha(baseline)!=APPROVED_SHA256:
        raise ValueError("Approved r67.12 ELF fingerprint changed")
    for off,ptr in zip(SCRIPT_POINTER_OFFSETS,APPROVED_POINTERS,strict=True):
        if struct.unpack_from("<I",baseline,off)[0]!=ptr:
            raise ValueError("Chamber localized script pointer drift")
    fo,va,size,reserve,flags=(
        struct.unpack_from("<I",baseline,k)[0] for k in (0x58,0x5c,0x64,0x68,0x6c))
    if (fo,va,fo+size,reserve,flags)!=(
        ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(baseline),ELF_SEGMENT_RESERVE,7
    ):raise ValueError("Translation memory-segment drift")
    for site,_ in STORY_CALLS:
        off=site-ELF_BIAS
        if (struct.unpack_from("<I",baseline,off)[0],
            struct.unpack_from("<I",baseline,off+4)[0])!=(ORIGINAL_JAL,0):
            raise ValueError(f"Original story call changed at {site:#x}")

    patched=bytearray(baseline)
    while len(patched)&3:patched.append(0)
    def append(payload:bytes)->int:
        address=va+len(patched)-fo
        if address&3 or address>=0x10000000:
            raise ValueError("Appended code not JAL-addressable")
        if len(patched)+len(payload)-fo>reserve:
            raise ValueError("Translation memory segment capacity exceeded")
        patched.extend(payload)
        return address

    # Append ctor first to get address, then clone original function with a
    # SINGLE JAL redirected to ctor+scale shim; all other words unchanged.
    ctor_va=append(make_pre_layout_constructor())
    original_fn=_check_relocatable_native_function(baseline)
    clone=bytearray(original_fn)
    struct.pack_into("<I",clone,CTOR_JAL_VA-CLONE_SOURCE_VA,_jal(ctor_va))
    clone_va=append(bytes(clone))
    sites=[]
    sizes=[]
    for callsite,y in STORY_CALLS:
        helper=make_story_dispatch(y,clone_va)
        helper_va=append(helper)
        struct.pack_into("<I",patched,callsite-ELF_BIAS,_jal(helper_va))
        sites.append(hex(helper_va));sizes.append(len(helper))

    struct.pack_into("<I",patched,0x64,len(patched)-fo)
    allowed=set(range(0x64,0x68))
    for site,_ in STORY_CALLS:allowed.update(range(site-ELF_BIAS,site-ELF_BIAS+4))
    changed=[i for i,(a,b) in enumerate(zip(baseline,patched)) if a!=b]
    if any(i not in allowed for i in changed):
        raise ValueError("Unrelated original ELF byte changed")
    for identity in (b"SLPM-66511",b"BISLPM-66511Save"):
        if identity not in patched:raise ValueError("Save namespace changed")
    info=dict(
        revision=HELPER_VERSION,
        source_sha256=APPROVED_SHA256,
        output_sha256=_sha(patched),
        output_size=len(patched),
        ctor_wrapper_va=hex(ctor_va),
        cloned_native_text_renderer_va=hex(clone_va),
        cloned_native_text_renderer_bytes=len(clone),
        original_native_text_renderer_untouched=True,
        shared_font_ctor_untouched=True,
        changed_original_elf_offsets=[hex(x) for x in changed],
        text_only_site_helpers=sites,
        helper_sizes=sizes,
        untouched_other_story_comments=True,
        only_three_exact_comment_pointer_matches=list(map(hex,APPROVED_POINTERS)),
        horizontal_scale_applied_before_glyph_layout=HORIZONTAL_SCALE,
        preserved_text_anchors=[y for _,y in STORY_CALLS],
        preserved_short_sentence_x=SHORT_MESSAGE_X,
        preserved_bubble_and_background=True,
        runtime_approved=False,
        static_validation_pending=True,
    )
    return bytes(patched),info

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    for opt in ("baseline","output","report"):
        parser.add_argument("--"+opt,required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("Refusing to overwrite candidate or evidence")
    candidate,info=apply(args.baseline.read_bytes())
    args.output.write_bytes(candidate)
    args.report.write_text(json.dumps(info,indent=2,sort_keys=True)+"\n")
    print(json.dumps(info,sort_keys=True))

if __name__=="__main__":
    main()
