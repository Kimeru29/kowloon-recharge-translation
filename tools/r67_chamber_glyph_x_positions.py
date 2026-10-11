"""r67.14f — fit Chamber of Lions text by compressing per-glyph X positions.

This is NOT another font-constructor/renderer/timer modification. We preserve
the near-perfect user-confirmed r67.14c text/bubble path and its two exact
story-comment JAL owners, native X/Y origins and 0.40 glyph scale.

The user's own slot-3 EE memory proves that the native renderer creates a
linked list of glyph nodes with their independent coordinates at node+0x10:
117,133,149,165,... 565, a constant 16.0px advance. The normal 0.40 font
scale changes glyph dimensions but not those already-computed node positions.

After the original 0x189E40 has finished generating glyphs and ONLY for the
three exact Chamber of Lions official script pointers, traverse font+0x04
glyph list via each node+0x120. Skip 0xFFFFFF0B (spaces) and 0xFFFFFF0F
sentinels; mutate X at node+0x10 ONLY if font atlas handle type is 0x00EAxxxx.
Perform x = text_origin_x + (x - text_origin_x) * 0.55.
Y, glyph size, bubble, blue backing, animation/timer and text remain intact.

The glyph loop has a strict 64-node cap and verifies EE pointer bounds; all
caller GPR/FPR registers and v0 original return value are preserved. The
approved native font constructor and story renderer are entirely unchanged.

Diagnostic until the user confirms on-screen rendering.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
from tools.r67_chamber_story_text_only import (
    APPROVED_SHA256, APPROVED_POINTERS, SCRIPT_POINTER_OFFSETS, STORY_CALLS,
    ORIGINAL_JAL, ORIGINAL_RENDERER_VA, ELF_BIAS, ELF_SEGMENT_FO,
    ELF_SEGMENT_VA, ELF_SEGMENT_RESERVE, SHORT_MESSAGE_POINTER,
    SHORT_MESSAGE_X, HORIZONTAL_SCALE, Assembly, _float_word, _i, _r, _jal,
)

GLYPH_ADVANCE_FACTOR = 0.55
ORIGINAL_GLYPH_ADVANCE = 16.0
GLYPH_NODE_KIND_HIGH16 = 0x00EA
MAX_GLYPH_NODES = 64
GLYPH_NODE_X = 0x10
GLYPH_NODE_NEXT = 0x120
FONT_NODE_HEAD = 0x04
FONT_ORIGIN_X = 0x14

def sha(value:bytes)->str:
    return hashlib.sha256(value).hexdigest()

def cop1_arith(funct:int,fd:int,fs:int,ft:int)->int:
    return (17<<26)|(16<<21)|(ft<<16)|(fs<<11)|(fd<<6)|funct

def compress_glyph_x()->bytes:
    """Called with t0=font object; do not change caller v0 or unrelated state.

    Preserve t1/t2/t3/t4/t5, FPU f0/f2/f4, and RA; all modified native data
    is exactly node+0x10 of validated atlas glyphs in the current font list.
    """
    m=Assembly()
    m.emit(_i(9,29,29,-0x40))     # addiu sp,sp,-64
    for reg,at in ((31,0),(9,4),(10,8),(11,12),(12,16),(13,20)):
        m.emit(_i(43,29,reg,at))  # sw preserved GPR
    for f,at in ((0,24),(2,28),(4,32)):
        m.emit(_i(57,29,f,at))    # swc1 preserved float
    m.emit(_i(49,8,0,FONT_ORIGIN_X)) # lwc1 f0,0x14(t0)
    m.const(9,_float_word(GLYPH_ADVANCE_FACTOR))
    m.emit((17<<26)|(4<<21)|(9<<16)|(2<<11))  # mtc1 t1,f2
    m.emit(_i(35,8,10,FONT_NODE_HEAD)) # lw t2,4(t0)
    m.emit(_i(9,0,11,0))         # t3=counter=0

    m.label("loop")
    m.branch(4,10,0,"done")     # beq t2,zero,done
    m.emit(0)
    m.emit(_i(10,11,12,MAX_GLYPH_NODES)) # slti t4,t3,64
    m.branch(4,12,0,"done")
    m.emit(0)

    # All pointer dereferences constrained to known 32 MB EE RAM region.
    m.const(12,0x00800000)
    m.emit(_r(10,12,13,0,43))    # sltu t5,t2,t4
    m.branch(5,13,0,"done")
    m.emit(0)
    m.const(12,0x02000000)
    m.emit(_r(10,12,13,0,43))    # sltu t5,t2,t4
    m.branch(4,13,0,"done")
    m.emit(0)

    m.emit(_i(35,10,12,0))      # lw t4,(t2) -- glyph atlas or sentinel
    m.emit(_r(0,12,12,16,2))    # srl t4,t4,16
    m.const(13,GLYPH_NODE_KIND_HIGH16)
    m.branch(5,12,13,"next")   # bypass sentinels and space objects
    m.emit(0)

    m.emit(_i(49,10,4,GLYPH_NODE_X))     # lwc1 f4,0x10(t2) original X
    m.emit(cop1_arith(1,4,4,0))         # sub.s f4,f4,f0
    m.emit(cop1_arith(2,4,4,2))         # mul.s f4,f4,f2
    m.emit(cop1_arith(0,4,4,0))         # add.s f4,f4,f0
    m.emit(_i(57,10,4,GLYPH_NODE_X))    # swc1 f4,0x10(t2), glyph X ONLY

    m.label("next")
    m.emit(_i(35,10,10,GLYPH_NODE_NEXT)) # lw t2,0x120(t2)
    m.emit(_i(9,11,11,1))         # t3++
    m.branch(4,0,0,"loop")
    m.emit(0)

    m.label("done")
    for f,at in ((4,32),(2,28),(0,24)):
        m.emit(_i(49,29,f,at))    # lwc1 restore
    for reg,at in ((13,20),(12,16),(11,12),(10,8),(9,4),(31,0)):
        m.emit(_i(35,29,reg,at))  # lw GPR restore
    m.emit(_i(9,29,29,0x40))
    m.emit(_r(31,0,0,0,8))
    m.emit(0)
    return m.done()

def make_story_helper(y:float,glyph_helper_va:int)->bytes:
    """14c accepted text owner, plus one safe post-layout node-only call."""
    m=Assembly()
    m.emit(_i(9,29,29,-0x20))
    m.emit(_i(43,29,31,0))
    m.emit(_i(43,29,8,4))
    m.emit(_i(43,29,9,8))
    m.emit(_i(43,29,0,12))
    for ptr in APPROVED_POINTERS:
        m.const(8,ptr)
        m.branch(4,9,8,"matched")
        m.emit(0)
    m.branch(4,0,0,"render")
    m.emit(0)
    m.label("matched")
    m.const(8,_float_word(y))
    m.emit((17<<26)|(4<<21)|(8<<16)|(13<<11)) # mtc1 t0,f13
    m.const(8,1)
    m.emit(_i(43,29,8,12))
    m.emit(_i(35,29,8,8))
    m.const(9,SHORT_MESSAGE_POINTER)
    m.branch(5,8,9,"render")
    m.emit(0)
    m.const(8,_float_word(SHORT_MESSAGE_X))
    m.emit((17<<26)|(4<<21)|(8<<16)|(12<<11)) # mtc1 t0,f12
    m.label("render")
    m.emit(_i(35,29,9,8))
    m.emit(_jal(ORIGINAL_RENDERER_VA))
    m.emit(0)
    m.emit(_i(35,29,8,12))    # matched flag
    m.branch(4,8,0,"done")
    m.emit(0)
    m.branch(4,2,0,"done")    # null renderer return
    m.emit(0)
    m.emit(_i(35,2,8,0x3c))  # t0=font
    m.branch(4,8,0,"done")
    m.emit(0)
    m.const(9,_float_word(HORIZONTAL_SCALE))
    m.emit(_i(43,8,9,0x48)) # exact approved 14c width of glyph itself
    m.emit(_jal(glyph_helper_va)) # NEW: reposition individual native glyphs
    m.emit(0)
    m.label("done")
    m.emit(_i(35,29,9,8))
    m.emit(_i(35,29,8,4))
    m.emit(_i(35,29,31,0))
    m.emit(_i(9,29,29,0x20))
    m.emit(_r(31,0,0,0,8))
    m.emit(0)
    return m.done()

def apply(baseline:bytes)->tuple[bytes,dict]:
    if sha(baseline)!=APPROVED_SHA256:
        raise ValueError("Approved r67.12 ELF fingerprint changed")
    for off,ptr in zip(SCRIPT_POINTER_OFFSETS,APPROVED_POINTERS,strict=True):
        if struct.unpack_from("<I",baseline,off)[0]!=ptr:
            raise ValueError("Official comment pointers changed")
    fo,va,size,reserve,flags=(
        struct.unpack_from("<I",baseline,k)[0] for k in (0x58,0x5c,0x64,0x68,0x6c)
    )
    if (fo,va,fo+size,reserve,flags)!=(
        ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(baseline),ELF_SEGMENT_RESERVE,7
    ):raise ValueError("Reserved segment drift")
    for site,_ in STORY_CALLS:
        off=site-ELF_BIAS
        if struct.unpack_from("<2I",baseline,off)!=(ORIGINAL_JAL,0):
            raise ValueError(f"Original text callsite drift: {site:#x}")
    patched=bytearray(baseline)
    while len(patched)&3:patched.append(0)
    def append(data:bytes)->int:
        target=va+len(patched)-fo
        if target&3 or target>=0x10000000:
            raise ValueError("Private code not in JAL segment")
        if len(patched)+len(data)-fo>reserve:
            raise ValueError("Private code exceeds reserved PT_LOAD")
        patched.extend(data)
        return target
    coords_va=append(compress_glyph_x())
    helpers=[]
    for site,y in STORY_CALLS:
        payload=make_story_helper(y,coords_va)
        target=append(payload)
        struct.pack_into("<I",patched,site-ELF_BIAS,_jal(target))
        helpers.append((hex(site),hex(target),len(payload)))
    struct.pack_into("<I",patched,0x64,len(patched)-fo)
    old_changed=[i for i,(a,b) in enumerate(zip(baseline,patched)) if a!=b]
    allowed=set(range(0x64,0x68))
    for site,_ in STORY_CALLS:allowed.update(range(site-ELF_BIAS,site-ELF_BIAS+4))
    if not old_changed or any(i not in allowed for i in old_changed):
        raise ValueError("Unexpected edits outside approved story callsites")
    for identity in (b"SLPM-66511",b"BISLPM-66511Save"):
        if identity not in patched:raise ValueError("Save namespace changed")
    return bytes(patched),dict(
        status="CANDIDATE_UNVERIFIED_RUNTIME",
        revision="r67.14f",
        source_approved_elf_sha=APPROVED_SHA256,
        candidate_elf_sha=sha(patched),
        compression_factor=GLYPH_ADVANCE_FACTOR,
        native_advance_before=ORIGINAL_GLYPH_ADVANCE,
        native_advance_after=ORIGINAL_GLYPH_ADVANCE*GLYPH_ADVANCE_FACTOR,
        glyph_nodes_max=MAX_GLYPH_NODES,
        glyph_atlas_class=hex(GLYPH_NODE_KIND_HIGH16),
        native_glyph_node_x_offset=hex(GLYPH_NODE_X),
        native_link_next_offset=hex(GLYPH_NODE_NEXT),
        private_compression_helper_va=hex(coords_va),
        isolated_story_callsite_helpers=helpers,
        existing_original_elf_changed_offsets=[hex(i) for i in old_changed],
        existing_green_blue_layers_and_dialogue_timing_unchanged=True,
        native_renderer_and_font_constructor_completely_unchanged=True,
        user_approved_14c_vertical_xorigins_and_glyph_scale_retained=True,
        runtime_verified=False,
        release_approved=False,
    )

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("baseline","output","report"):
        p.add_argument("--"+arg,required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():raise FileExistsError("Diagnostic cannot overwrite")
    blob,meta=apply(a.baseline.read_bytes())
    a.output.write_bytes(blob)
    a.report.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    print(json.dumps(meta,sort_keys=True))

if __name__=="__main__":
    main()
