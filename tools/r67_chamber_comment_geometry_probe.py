"""r67 Chamber of Lions automatic-comment-only geometry probe.

Native story-comment text is created with style=0, origin=(117,313), and
horizontal scale=1.0, causing a 29-character English line to overflow the
pre-existing green bubble. A single native constructor instruction is redirected
to a clone helper. ALL native non-matching font objects receive their unchanged
original x/y/scale and continue via the same original instruction path.

Preserve original Japanese resources, official English sentence, H.A.N.T.,
accepted AFK/L1, user-approved START-history and save namespace.
Not a release: needs in-game scene validation and final centering calibration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

BASELINE_SHA="d531e8545c86322d09527bc2a8c32ee01e3d5fbda67f735a0a92acc2519b2179"
SEGMENT_FO=0x803150
SEGMENT_VA=0x902F00
SEGMENT_MAX_SIZE=0x100000
BIAS=0xFFF80
HOOK_VA=0x188CEC
NEXT_VA=0x188CF4
ORIGINAL_HOOK=0xAE020048 # sw v0,0x48(s0), followed by unchanged sw v0,0x4c(s0)
UNALTERED_DELAY_SLOT=0xAE02004C
OLD_X=117.0
OLD_Y=313.0
NEW_Y=285.0
NEW_X_SCALE=0.68
MATCH_STYLE=0

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def word_f32(value:float)->int:
    return struct.unpack("<I",struct.pack("<f",value))[0]

def ins_i(op:int, rs:int, rt:int, imm:int)->int:
    assert -0x8000<=imm<=0xFFFF
    return (op<<26)|(rs<<21)|(rt<<16)|(imm&0xFFFF)

def ins_r(rs:int,rt:int,rd:int,sa:int,fn:int)->int:
    return (rs<<21)|(rt<<16)|(rd<<11)|(sa<<6)|fn

def ins_j(target:int, link:bool=False)->int:
    if target&3 or target>=0x10000000:
        raise ValueError(f"JAL target unreachable: {target:#x}")
    return (3 if link else 2)<<26 | (target>>2)

def make_helper()->bytes:
    # MIPS GPR: s0=object, v0=1.0f, t0=$8, t1=$9. Preserve temp regs.
    words:list[int]=[]
    labels:dict[str,int]={}
    pending:list[tuple[int,int,int,str]]=[]
    def add(w:int):
        words.append(w)
    def mark(name:str):
        labels[name]=len(words)
    def branch_not_equal(rs:int,rt:int,label:str):
        pending.append((len(words),rs,rt,label));add(0)
    def load_const(rt:int,value:int):
        add(ins_i(15,0,rt,value>>16))
        if value&0xffff:add(ins_i(13,rt,rt,value&0xffff))
    add(ins_i(43,16,2,0x48))           # original sw v0,0x48(s0)
    add(ins_i(9,29,29,-0x20))          # addiu sp,sp,-0x20
    add(ins_i(43,29,8,0))              # save t0
    add(ins_i(43,29,9,4))              # save t1
    add(ins_i(35,16,8,0xc))            # lw t0,style(s0)
    branch_not_equal(8,0,"restore");add(0)
    add(ins_i(35,16,8,0x14))           # lw t0,x(s0)
    load_const(9,word_f32(OLD_X))
    branch_not_equal(8,9,"restore");add(0)
    add(ins_i(35,16,8,0x18))           # lw t0,y(s0)
    load_const(9,word_f32(OLD_Y))
    branch_not_equal(8,9,"restore");add(0)
    load_const(8,word_f32(NEW_Y))
    add(ins_i(43,16,8,0x18))           # sw new Y
    load_const(8,word_f32(NEW_X_SCALE))
    add(ins_i(43,16,8,0x48))           # sw constrained X scale
    mark("restore")
    add(ins_i(35,29,8,0))
    add(ins_i(35,29,9,4))
    add(ins_i(9,29,29,0x20))
    add(ins_j(NEXT_VA))
    add(0)
    for idx,rs,rt,label in pending:
        displacement=labels[label]-(idx+1)
        if not -0x8000<=displacement<=0x7fff:raise ValueError("Unsafe branch distance")
        words[idx]=ins_i(5,rs,rt,displacement)
    assert words[0]==ORIGINAL_HOOK
    assert words[-2]==ins_j(NEXT_VA)
    return struct.pack("<"+"I"*len(words),*words)

def apply(baseline:bytes)->tuple[bytes,dict]:
    if sha(baseline)!=BASELINE_SHA:
        raise ValueError("Unexpected approved r67.12 baseline checksum")
    elf=bytearray(baseline)
    filesz=struct.unpack_from("<I",elf,0x64)[0]
    fo=struct.unpack_from("<I",elf,0x58)[0]
    va=struct.unpack_from("<I",elf,0x5c)[0]
    reserve=struct.unpack_from("<I",elf,0x68)[0]
    if (fo,va,filesz,reserve)!=(SEGMENT_FO,SEGMENT_VA,len(elf)-SEGMENT_FO,SEGMENT_MAX_SIZE):
        raise ValueError("Translation PT_LOAD drift")
    source=HOOK_VA-BIAS
    if (struct.unpack_from("<I",elf,source)[0],struct.unpack_from("<I",elf,source+4)[0])!=(ORIGINAL_HOOK,UNALTERED_DELAY_SLOT):
        raise ValueError("Native constructor hook preimage mismatch")
    # Guard 3 official Chamber of Lions text owners, including split line.
    for off in (0x3D3438,0x3D343C,0x3D3448):
        if baseline[off:off+4]!=elf[off:off+4]:
            raise ValueError("Official comment pointer drift")
    while len(elf)&3:elf.append(0)
    target=va+len(elf)-fo
    if len(elf)-fo+len(make_helper())>reserve:
        raise ValueError("Translation PT_LOAD exhausted")
    elf.extend(make_helper())
    struct.pack_into("<I",elf,source,ins_j(target))
    struct.pack_into("<I",elf,0x64,len(elf)-fo)
    original_changed=[i for i,(a,b) in enumerate(zip(baseline,elf)) if a!=b]
    allowed=set(range(source,source+4))|set(range(0x64,0x68))
    if any(i not in allowed for i in original_changed):
        raise ValueError("Unrelated ELF byte mutated")
    for identity in (b"SLPM-66511",b"BISLPM-66511Save"):
        if identity not in elf:raise ValueError("Save namespace lost")
    return bytes(elf),dict(
       status="DIAGNOSTIC_ONLY_USER_VISUAL_VERIFICATION_REQUIRED",
       input_sha256=BASELINE_SHA,
       output_sha256=sha(elf),
       patch_site_va=hex(HOOK_VA),
       helper_va=hex(target),
       helper_bytes=len(make_helper()),
       original_elf_modified_byte_offsets=[hex(i) for i in original_changed],
       guarded_original_style=MATCH_STYLE,
       guarded_original_xy=[OLD_X,OLD_Y],
       new_y=NEW_Y,
       new_x_scale=NEW_X_SCALE,
       non_matching_font_objects_unchanged=True,
       normal_story_dialogue_and_hant_unchanged=True,
       history_layout_lock_required=True,
       runtime_verified=False,
       release_approved=False
    )

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("baseline","output","report"):
        parser.add_argument("--"+name,type=Path,required=True)
    opts=parser.parse_args()
    if opts.output.exists() or opts.report.exists():
        raise FileExistsError("Refusing overwrite")
    data,meta=apply(opts.baseline.read_bytes())
    opts.output.write_bytes(data)
    opts.report.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    print(json.dumps(meta,sort_keys=True))

if __name__=="__main__":
    main()
