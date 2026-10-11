"""r67 Chamber of Lions old-man STORY-COMMENT-only text overlay candidate.

Native H_TalkBuddyTask story-comment path (<601) has two text call sites,
separate from AFK free talk and all green/blue sprite construction. Replace
ONLY those two JALs with helpers that recognize the THREE exact relocated
script pointers for "Make sure you're always ready / to switch into battle
mode at / any time." All other source pointers call the original renderer
with untouched registers and leave returned font objects unchanged.

Matched lines get Y=280/300 BEFORE 0x189E40 creates the font, then X scale
0.55 on the returned font (nested +0x3C) AFTER construction, following the
same proven AFK approach without patching any backing-resource geometry.
The short third sentence is horizontally centered at X=205. Only the intended
comment text is affected; no sprite, blue panel, green border, atlas, normal
dialogue, AFK free talk, H.A.N.T., or approved history bytes are changed.

Diagnostic until visual proof, NOT a release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

APPROVED_SHA256 = "d531e8545c86322d09527bc2a8c32ee01e3d5fbda67f735a0a92acc2519b2179"
ELF_BIAS = 0xFFF80
ELF_SEGMENT_FO = 0x803150
ELF_SEGMENT_VA = 0x902F00
ELF_SEGMENT_RESERVE = 0x100000
ORIGINAL_RENDERER_VA = 0x189E40
STORY_CALLS = ((0x1661BC, 280.0), (0x16628C, 300.0))
ORIGINAL_JAL = 0x0C062790  # jal 0x189E40
SCRIPT_POINTER_OFFSETS = (0x3D3438, 0x3D343C, 0x3D3448)
APPROVED_POINTERS = (0x92D0C8, 0x92D104, 0x92D140)
SHORT_MESSAGE_POINTER = APPROVED_POINTERS[-1]
HORIZONTAL_SCALE = 0.55
SHORT_MESSAGE_X = 205.0

def _sha(data:bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _float_word(x:float) -> int:
    return struct.unpack("<I",struct.pack("<f",x))[0]

def _i(op:int,rs:int,rt:int,imm:int)->int:
    if not -0x8000<=imm<=0xffff:
        raise ValueError(f"immediate out of range {imm}")
    return (op<<26)|(rs<<21)|(rt<<16)|(imm&0xffff)

def _r(rs:int,rt:int,rd:int,shift:int,fn:int)->int:
    return rs<<21|rt<<16|rd<<11|shift<<6|fn

def _jal(va:int)->int:
    if va&3 or (va>>28) != 0 or va>=0x10000000:raise ValueError("JAL VA invalid")
    return (3<<26)|((va>>2)&0x03ffffff)

class Assembly:
    def __init__(self):
        self.words:list[int]=[]
        self.labels:dict[str,int]={}
        self.jumps:list[tuple[int,str,int,int]]=[]
    def emit(self,w:int):self.words.append(w)
    def label(self,n:str):
        if n in self.labels:raise ValueError(f"Duplicate label {n}")
        self.labels[n]=len(self.words)
    def branch(self,op:int,rs:int,rt:int,label:str):
        self.jumps.append((len(self.words),label,op,rs<<5|rt))
        self.emit(0)
    def const(self,reg:int,word:int):
        self.emit(_i(15,0,reg,word>>16))
        if word&0xffff:self.emit(_i(13,reg,reg,word&0xffff))
    def done(self)->bytes:
        for idx,label,op,joined in self.jumps:
            imm=self.labels[label]-(idx+1)
            self.words[idx]=_i(op,joined>>5,joined&31,imm)
        if self.words[-2]!=0x03e00008 or self.words[-1]!=0:
            raise ValueError("Helper epilogue lost")
        return struct.pack("<"+"I"*len(self.words),*self.words)

def make_helper(text_y:float)->bytes:
    m=Assembly()
    # s0+0x04 holds the story-record index; the caller has already taken the
    # <0x259 branch. t1 holds the exact source pointer loaded from its table.
    # Stack frame preserves caller RA, t0, t1 and selection.
    m.emit(_i(9,29,29,-0x20))      # addiu sp,sp,-32
    m.emit(_i(43,29,31,0))        # sw ra,0(sp)
    m.emit(_i(43,29,8,4))         # sw t0,4(sp)
    m.emit(_i(43,29,9,8))         # sw t1,8(sp)
    m.emit(_i(43,29,0,12))        # sw zero,12(sp)  flag
    for ptr in APPROVED_POINTERS:
        m.const(8,ptr)
        m.branch(4,9,8,"matched") # beq t1,t0,matched
        m.emit(0)                 # delay slot nop
    m.branch(4,0,0,"render")      # unconditional beq zero,zero
    m.emit(0)
    m.label("matched")
    m.const(8,_float_word(text_y))
    m.emit(_r(4,8,13,0,0))        # placeholder updated below to MTC1
    # mtc1 t0,f13, COP1 transfer opcode 17 / rs=4 / rt=t0 / fs=f13.
    m.words[-1]=(17<<26)|(4<<21)|(8<<16)|(13<<11)
    m.const(8,1)
    m.emit(_i(43,29,8,12))        # sw t0,12(sp), mark matched
    m.emit(_i(35,29,8,8))         # lw t0,8(sp), original source pointer
    m.const(9,SHORT_MESSAGE_POINTER)
    m.branch(5,8,9,"render")      # bne t0,t1,render
    m.emit(0)
    m.const(8,_float_word(SHORT_MESSAGE_X))
    m.emit((17<<26)|(4<<21)|(8<<16)|(12<<11)) # mtc1 t0,f12
    m.label("render")
    m.emit(_i(35,29,9,8))         # restore caller t1 before native text renderer
    m.emit(_jal(ORIGINAL_RENDERER_VA))
    m.emit(0)
    m.emit(_i(35,29,8,12))       # lw t0, matched flag
    m.branch(4,8,0,"done")
    m.emit(0)
    m.branch(4,2,0,"done")        # if renderer failed, leave unchanged
    m.emit(0)
    m.emit(_i(35,2,8,0x3c))      # lw t0,0x3c(v0), font object
    m.branch(4,8,0,"done")
    m.emit(0)
    m.const(9,_float_word(HORIZONTAL_SCALE))
    m.emit(_i(43,8,9,0x48))      # sw t1,0x48(t0), font-only X scale
    m.label("done")
    m.emit(_i(35,29,9,8))
    m.emit(_i(35,29,8,4))
    m.emit(_i(35,29,31,0))
    m.emit(_i(9,29,29,0x20))
    m.emit(_r(31,0,0,0,8))       # jr ra
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
    if (fo,va,fo+size,reserve,flags)!=(ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(baseline),ELF_SEGMENT_RESERVE,7):
        raise ValueError("Translation memory-segment drift")
    for site,_y in STORY_CALLS:
        off=site-ELF_BIAS
        if struct.unpack_from("<I",baseline,off)[0]!=ORIGINAL_JAL or struct.unpack_from("<I",baseline,off+4)[0]!=0:
            raise ValueError(f"Unapproved story-only callsite at {site:#x}")
    patched=bytearray(baseline)
    while len(patched)&3:patched.append(0)
    targets=[]
    sizes=[]
    for callsite,y in STORY_CALLS:
        helper=make_helper(y)
        target=va+len(patched)-fo
        if target&3 or target>=0x10000000:raise ValueError("Unreachable helper")
        if len(patched)+len(helper)-fo>reserve:raise ValueError("Segment reserve insufficient")
        patched.extend(helper)
        struct.pack_into("<I",patched,callsite-ELF_BIAS,_jal(target))
        targets.append(hex(target));sizes.append(len(helper))
    struct.pack_into("<I",patched,0x64,len(patched)-fo)
    allowed=set(range(0x64,0x68))
    for site,_ in STORY_CALLS:allowed.update(range(site-ELF_BIAS,site-ELF_BIAS+4))
    modifications=[i for i,(a,b) in enumerate(zip(baseline,patched)) if a!=b]
    if any(i not in allowed for i in modifications):
        raise ValueError("Unexpected modifications to previously approved ELF")
    if b"SLPM-66511" not in patched or b"BISLPM-66511Save" not in patched:
        raise ValueError("Save identifier missing")
    return bytes(patched),dict(
        state="DIAGNOSTIC_ONLY_PENDING_IN_GAME_VISUAL_TEST",
        old_elf_sha256=APPROVED_SHA256,
        new_elf_sha256=_sha(patched),
        story_only_callsites=[hex(s) for s,_ in STORY_CALLS],
        original_story_renderer_va=hex(ORIGINAL_RENDERER_VA),
        comment_exact_source_pointers=list(map(hex,APPROVED_POINTERS)),
        appended_helper_vas=targets,appended_sizes=sizes,
        modified_existing_offsets=list(map(hex,modifications)),
        text_y=[y for _,y in STORY_CALLS],
        font_x_scale=HORIZONTAL_SCALE,short_third_line_x=SHORT_MESSAGE_X,
        original_green_and_blue_sprite_bytes_unchanged=True,
        original_font_constructor_bytes_unchanged=True,
        afk_and_l1_paths_unchanged=True,
        requires_locked_history_check=True,
        requires_hant_and_r59_regression=True,
        runtime_verified=False,
        release_approved=False,
    )

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():raise FileExistsError("Do not overwrite diagnostic")
    payload,meta=apply(a.baseline.read_bytes())
    a.output.write_bytes(payload)
    a.report.write_text(json.dumps(meta,sort_keys=True,indent=2)+"\n")
    print(json.dumps(meta,sort_keys=True))

if __name__=="__main__":
    main()
