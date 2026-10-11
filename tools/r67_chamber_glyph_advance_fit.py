"""r67.14j: comment-only horizontal glyph-X fitting after proven t0 correction.

r67.14i visibly restored correct story text and vertical placement but the
29-character first line overflows the original bubble horizontally. Native
glyph nodes store independent X coordinates at node+0x10 and Y at +0x14.
Their linked list starts at nested font+0x04 and advances via node+0x120,
as verified in the user's real Chamber savestates.

On the exact r67.14i ELF, redirect ONLY the two existing, matched-comment
font-X-scale stores into a small post-render X-only helper. The following
original 'lw s7,0x10(sp)' remains as the JAL delay slot; unmatched paths
continue to branch to it. The helper performs that original font-X-scale
store first and then changes only 0x00EAxxxx atlas glyph node X coordinates,
relative to the existing font origin X. All other objects, registers, Y
coords, backing, duration, history and unrelated font renders remain intact.

Unlike the rejected r67.14f, r67.14j begins from the demonstrated r67.14i
argument-preserving implementation. This is a diagnostic until visually
approved in a real cold-boot game.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from tools.r67_chamber_pre_glyph_font_target import sha
from tools.r67_chamber_story_text_only import (
    Assembly, _float_word, _i, _r, _jal, ELF_SEGMENT_FO, ELF_SEGMENT_VA,
    ELF_SEGMENT_RESERVE, ELF_BIAS
)

INPUT_SHA256 = "3f11b7ff426a8249b908d98b89ad194a2bbef9593297b2adb95003424e39abe8"
WRAPPERS = ((0x963D20, 0x963DDC), (0x963DFC, 0x963EB8))
COMMENT_GLYPH_ADVANCE_FRACTION = 0.70
MAX_NODES = 64
ATLAS_TAG_HIGH16 = 0x00EA
SCALE_STORE = _i(43, 8, 9, 0x48)  # sw t1,+0x48(t0): existing horizontal glyph scale 0.40
PRESERVE_S7 = _i(35, 29, 23, 0x10)
RESTORED_SOURCE_T0 = _i(35, 29, 8, 4)

def cop1(funct: int, dest: int, first: int, second: int) -> int:
    return (17<<26)|(16<<21)|(second<<16)|(first<<11)|(dest<<6)|funct

def horizontal_glyph_helper() -> bytes:
    a = Assembly()
    a.emit(SCALE_STORE)                 # exact existing font scale store
    a.emit(_i(9,29,29,-0x40))           # aligned stack frame
    for reg,offset in ((31,0),(9,4),(10,8),(11,12),(12,16),(13,20)):
        a.emit(_i(43,29,reg,offset))
    for freg,offset in ((0,24),(2,28),(4,32)):
        a.emit(_i(57,29,freg,offset))  # swc1
    a.emit(_i(49,8,0,0x14))          # lwc1 f0, font.originX
    a.const(9,_float_word(COMMENT_GLYPH_ADVANCE_FRACTION))
    a.emit((17<<26)|(4<<21)|(9<<16)|(2<<11)) # mtc1 t1,f2
    a.emit(_i(35,8,10,4))           # lw t2,font.glyphNodeHead
    a.emit(_i(9,0,11,0))            # t3 = 0, capped node visits
    a.label("loop")
    a.branch(4,10,0,"done")        # null terminates
    a.emit(0)
    a.emit(_i(10,11,12,MAX_NODES))  # slti t4,t3,64
    a.branch(4,12,0,"done")
    a.emit(0)
    a.emit(_i(12,10,12,3))         # andi t4,t2,3, reject unaligned nodes
    a.branch(5,12,0,"done")
    a.emit(0)
    a.const(12,0x00800000)          # EE RAM lower bound
    a.emit(_r(10,12,13,0,43))      # sltu t5,t2,t4
    a.branch(5,13,0,"done")
    a.emit(0)
    a.const(12,0x01FFFE00)          # bound allows node+0x120, X, Y reads
    a.emit(_r(10,12,13,0,43))
    a.branch(4,13,0,"done")
    a.emit(0)
    a.emit(_i(35,10,12,0))        # tag
    a.emit(_r(0,12,12,16,2))      # srl t4,tag,16
    a.const(13,ATLAS_TAG_HIGH16)
    a.branch(5,12,13,"next")      # ignore space/sentinel nodes
    a.emit(0)
    a.emit(_i(49,10,4,0x10))      # lwc1 f4,node.x
    a.emit(cop1(1,4,4,0))         # sub.s f4,f4,f0
    a.emit(cop1(2,4,4,2))         # mul.s f4,f4,f2
    a.emit(cop1(0,4,4,0))         # add.s f4,f4,f0
    a.emit(_i(57,10,4,0x10))      # swc1 f4,node.x ONLY
    a.label("next")
    a.emit(_i(35,10,10,0x120))    # next glyph node
    a.emit(_i(9,11,11,1))
    a.branch(4,0,0,"loop")
    a.emit(0)
    a.label("done")
    for freg,offset in ((4,32),(2,28),(0,24)):
        a.emit(_i(49,29,freg,offset))
    for reg,offset in ((13,20),(12,16),(11,12),(10,8),(9,4),(31,0)):
        a.emit(_i(35,29,reg,offset))
    a.emit(_i(9,29,29,0x40))
    a.emit(_r(31,0,0,0,8))
    a.emit(0)
    return a.done()

def patch(source: bytes) -> tuple[bytes,dict]:
    if sha(source)!=INPUT_SHA256:
        raise ValueError("Refusing non-approved r67.14i ELF or modified source")
    data=bytearray(source)
    fo,va,size,reserve,flags=(
        struct.unpack_from('<I',source,off)[0] for off in (0x58,0x5C,0x64,0x68,0x6C)
    )
    if (fo,va,fo+size,reserve,flags)!=(ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(source),ELF_SEGMENT_RESERVE,7):
        raise ValueError("Private executable segment drift")
    for wrapper,site in WRAPPERS:
        if struct.unpack_from('<2I',source,ELF_SEGMENT_FO+site-ELF_SEGMENT_VA)!=(SCALE_STORE,PRESERVE_S7):
            raise ValueError(f"Matched-only scale store/branch target drift at {site:#x}")
        if struct.unpack_from('<I',source,ELF_SEGMENT_FO+wrapper+140-ELF_SEGMENT_VA+4)[0]!=RESTORED_SOURCE_T0:
            raise ValueError("r67.14i native t0 text argument restore missing")
    while len(data)&3:data.append(0)
    helper_va=va+len(data)-fo
    if helper_va&3 or helper_va>=0x10000000:
        raise ValueError("Private JAL out of reach")
    helper=horizontal_glyph_helper()
    if len(data)+len(helper)-fo>reserve:
        raise ValueError("Reserved ELF segment exceeded")
    data.extend(helper)
    for _,site in WRAPPERS:
        struct.pack_into('<I',data,ELF_SEGMENT_FO+site-ELF_SEGMENT_VA,_jal(helper_va))
    struct.pack_into('<I',data,0x64,len(data)-fo)
    original_mutations=[
        i for i,(a,b) in enumerate(zip(source,data)) if a!=b
    ]
    allowed=set(range(0x64,0x68))
    for _,site in WRAPPERS: allowed.update(range(ELF_SEGMENT_FO+site-ELF_SEGMENT_VA,ELF_SEGMENT_FO+site-ELF_SEGMENT_VA+4))
    if not original_mutations or set(original_mutations)-allowed:
        raise ValueError("Original code changed outside comment helper JALs and ELF size")
    result={
        "revision":"r67.14j",
        "status":"DIAGNOSTIC_AWAITING_REAL_GAME_VISUAL_ACCEPTANCE",
        "source_14i_sha256":sha(source),
        "staged_elf_sha256":sha(data),
        "helper_va":hex(helper_va),
        "helper_bytes":len(helper),
        "compress_only_matched_glyph_x":True,
        "fraction":COMMENT_GLYPH_ADVANCE_FRACTION,
        "glyph_node_y_never_written":True,
        "font_scale_store_preserved":hex(SCALE_STORE),
        "saved_text_t0_restore_preserved":True,
        "unmatched_branch_targets_preserved":True,
        "native_code_bubble_blue_backing_timers_history_hant_preserved":True,
        "changed_original_byte_offsets":[hex(i) for i in original_mutations],
        "runtime_verified":False,
        "release_approved":False
    }
    return bytes(data),result

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('input','output','report'):p.add_argument('--'+arg,required=True,type=Path)
    args=p.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("Refusing to overwrite diagnostic artifacts")
    candidate,report=patch(args.input.read_bytes())
    args.output.write_bytes(candidate)
    args.report.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":main()
