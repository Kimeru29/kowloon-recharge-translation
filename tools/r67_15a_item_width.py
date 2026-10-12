"""r67.15a — Generic bounded item-name scaling at two proven UI widths.

Native owners:
  * M_ObjGetDraw & M_DngItemUse: 0x2A2A6C / 0x2A6060 (narrow action names).
    Preserve accepted Lion Statue 0.72 exact, dynamically scale any other
    >8-fullwidth-cell native CP932 catalog name to 8/cellCount.
  * M_ItemList selection name: 0x29DC44, fed by lookup 0x134AB0.
    Dynamically scale labels longer than 15 cells to 15/cellCount, e.g.
    Hydrochloric Acid (17) and long catalog titles.

Name source text and all 500 catalog pointers remain unchanged. Original
setter 0x18A080 is called first. Only x scale (not y, position, font, sprite,
AFK, save or any state) is adjusted as a generic class-width invariant.

The two already-approved Lion callsites necessarily receive one documented
new JAL target; their previous accepted helper remains present and intact.
This is a narrow, explicit user-requested diagnostic exception, NOT a
regeneration or weakening of the previous r67.14t approval manifest.
"""
from __future__ import annotations

import argparse,json,struct,hashlib
from pathlib import Path
from tools.r67_chamber_story_text_only import (
    Assembly,ELF_SEGMENT_FO as FO,ELF_SEGMENT_VA as VA,
    ELF_SEGMENT_RESERVE as RESERVE,ELF_BIAS,_i,_r,_jal,_float_word,
)
from tools.r67_lion_statue_ui import (
    ITEM_NAME_POINTER_OFFSET,ORIGINAL_TEXT_SETTER,
    NATIVE_XY_SCALING_SETTER,sha,item_pointer,CALL_SITES,
)
from tools.r67_14t_stone_tablet_fit import read_string

GENERIC_NARROW_SITES=CALL_SITES
GENERIC_WIDE_SITE=0x29DC44
NARROW_CELLS=8
WIDE_CELLS=15
LION_SCALE=0.72
WIDE_OLD_JAL=_jal(ORIGINAL_TEXT_SETTER)


def _cop1_mtc1(rt:int,fs:int)->int:
    return (17<<26)|(4<<21)|(rt<<16)|(fs<<11)


def _cop1_cvt_s_w(fd:int,fs:int)->int:
    return (17<<26)|(20<<21)|(fs<<11)|(fd<<6)|0x20


def _cop1_div_s(fd:int,fs:int,ft:int)->int:
    return (17<<26)|(16<<21)|(ft<<16)|(fs<<11)|(fd<<6)|0x03


def helper(item_lion_ptr:int,budget:int,*,lion_exception:bool)->bytes:
    m=Assembly()
    m.emit(_i(9,29,29,-0x30))
    m.emit(_i(63,29,31,0x20))
    m.emit(_i(63,29,16,0x10))
    m.emit(_i(63,29,17,0x18))
    m.emit(_r(4,0,16,0,37))                         # s0=a0 text object
    m.emit(_r(5,0,17,0,37))                         # s1=a1 item name
    m.emit(_jal(ORIGINAL_TEXT_SETTER))
    m.emit(0)
    m.branch(4,16,0,"done")                         # null text handle
    m.emit(0)
    m.branch(4,17,0,"done")                         # null source pointer
    m.emit(0)
    if lion_exception:
        m.const(8,item_lion_ptr)
        m.branch(4,17,8,"lion")
        m.emit(0)
    m.emit(_i(9,0,9,0))                             # t1=0 glyph cells
    m.emit(_r(17,0,10,0,37))                       # t2=s1 source cursor
    m.label("measure")
    m.emit(_i(36,10,8,0))                          # lbu t0,0(t2)
    m.branch(4,8,0,"measured")
    m.emit(0)
    m.emit(_i(9,9,9,1))                            # addiu t1,t1,1
    m.emit(_i(9,10,10,2))                          # addiu t2,t2,2
    m.branch(4,0,0,"measure")
    m.emit(0)
    m.label("measured")
    m.emit(_i(10,9,8,budget+1))                    # slti t0,t1,budget+1
    m.branch(5,8,0,"done")                         # name already fits
    m.emit(0)
    m.emit(_r(16,0,4,0,37))                        # a0=text object
    m.const(8,_float_word(float(budget)))
    m.emit(_cop1_mtc1(8,12))                       # f12=float(cell budget)
    m.emit(_cop1_mtc1(9,14))                       # f14=int actual cells
    m.emit(0)
    m.emit(_cop1_cvt_s_w(14,14))                   # f14=float(cells)
    m.emit(0)
    m.emit(_cop1_div_s(12,12,14))                  # f12=budget / actual
    m.emit(0)
    m.const(8,_float_word(1.0))
    m.emit(_cop1_mtc1(8,13))                       # f13=1.0
    m.emit(_jal(NATIVE_XY_SCALING_SETTER))
    m.emit(0)
    m.branch(4,0,0,"done")
    m.emit(0)
    if lion_exception:
        m.label("lion")
        m.emit(_r(16,0,4,0,37))
        m.const(8,_float_word(LION_SCALE))
        m.emit(_cop1_mtc1(8,12))
        m.const(8,_float_word(1.0))
        m.emit(_cop1_mtc1(8,13))
        m.emit(_jal(NATIVE_XY_SCALING_SETTER))
        m.emit(0)
    m.label("done")
    m.emit(_i(55,29,17,0x18))
    m.emit(_i(55,29,16,0x10))
    m.emit(_i(55,29,31,0x20))
    m.emit(_i(9,29,29,0x30))
    m.emit(_r(31,0,0,0,8))
    m.emit(0)
    return m.done()


def apply(source:bytes,source_sha:str,old_lion_helper_va:int)->tuple[bytes,dict]:
    if sha(source)!=source_sha:
        raise ValueError("Unknown previously approved z source ELF preimage")
    ptr=item_pointer(source)
    if old_lion_helper_va!=0x963FD0:
        raise ValueError("Unrecognized approved Lion helper address")
    if any(struct.unpack_from("<I",source,v-ELF_BIAS)[0]!=_jal(old_lion_helper_va)
           for v in GENERIC_NARROW_SITES):
        raise ValueError("One of the immutable original Lion callsites drifted")
    if struct.unpack_from("<I",source,GENERIC_WIDE_SITE-ELF_BIAS)[0]!=WIDE_OLD_JAL:
        raise ValueError("Original native inventory name setter changed")
    data=bytearray(source)
    while len(data)&3:data.append(0)
    helpers=[]
    for title,budget,sites,lion in (
        ("narrow",NARROW_CELLS,GENERIC_NARROW_SITES,True),
        ("wide",WIDE_CELLS,(GENERIC_WIDE_SITE,),False)
    ):
        va=VA+len(data)-FO
        raw=helper(ptr,budget,lion_exception=lion)
        data.extend(raw)
        for site in sites:
            struct.pack_into("<I",data,site-ELF_BIAS,_jal(va))
        helpers.append(dict(label=title,va=hex(va),byte_count=len(raw),
                            native_owners=list(map(hex,sites)),cell_budget=budget,
                            accepted_lion_scale=LION_SCALE if lion else None))
    if len(data)-FO>RESERVE:raise ValueError("ELF translation PT_LOAD budget exhausted")
    struct.pack_into("<I",data,0x64,len(data)-FO)
    approved_allow=set(range(0x64,0x68))
    for site in (*GENERIC_NARROW_SITES,GENERIC_WIDE_SITE):
        approved_allow.update(range(site-ELF_BIAS,site-ELF_BIAS+4))
    changed=[i for i,(a,b) in enumerate(zip(source,data)) if a!=b]
    if not changed or set(changed)-approved_allow:
        raise ValueError("Unauthorized prior code/data mutation")
    result=bytes(data)
    names=[]
    for item_id in (264,274,413):
        p=struct.unpack_from("<I",result,0x3912B4+item_id*4)[0]
        caption=read_string(result,p).decode('cp932')
        names.append(dict(id=item_id,caption=caption,glyphs=len(caption),
                          narrow=float(LION_SCALE) if item_id==413 else min(1,NARROW_CELLS/len(caption)),
                          wide=min(1,WIDE_CELLS/len(caption))))
    return result,dict(status="DIAGNOSTIC_NEEDS_ITEM_SELECTION_SCREENSHOTS",
        source_sha256=source_sha,result_sha256=sha(result),
        helper_owners=helpers,
        changed_existing_byte_offsets=list(map(hex,changed)),
        appended_bytes=len(result)-len(source),
        item_test_samples=names,
        all_500_original_item_name_pointers_unchanged=True,
        previously_approved_Lion_0_72_scale_preserved=True,
        screen_visual_approval=False)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("input","output","report"):p.add_argument("--"+n,type=Path,required=True)
    p.add_argument("--source-sha",required=True)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():raise FileExistsError("Do not overwrite")
    b,meta=apply(a.input.read_bytes(),a.source_sha,0x963FD0)
    a.output.write_bytes(b)
    a.report.write_text(json.dumps(meta,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in meta.items() if k not in ("helper_owners",)},sort_keys=True))
