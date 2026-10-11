"""Bounded PS2 dialogue-history (START modal) two-canvas English presentation.

This is an unapproved PCSX2 candidate, distinct from the r66 ADV/DG renderer:
the second native two-canvas constructor at VA 0x259C54 creates text using
orientation a2=1 and original Japanese-column X progression. Route only that
existing constructor's JAL through an append-only 72-byte shim; no ordinary
ADV, AFK/L1, story data, save identity or unrelated constructor is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.companion_hud import _mips_i, _mips_mtc1


EXPECTED_INPUT_SHA = "be8152e77d1fe675871f5bd0eab2e857a3911a9c8f44264c602a0e83bb92a759"
JAL_FILE_OFFSET = 0x159D54
JAL_PREIMAGE = 0x0C062FC4  # 0x18BF10 (native font-canvas constructor)
NATIVE_FONT_VA = 0x18BF10
LAYOUT_INPUTS = {
    0x159CE0: 0x3C02421C,  # original 39.0f column multiplier
    0x159D40: 0x24050002,  # font style 2
    0x159D48: 0x24060001,  # vertical flag in paused dialogue
    0x159D50: 0x2407FFFF,  # native a3 remains unmodified
    0x159D6C: 0x2A020002,  # exactly two speaker/body native canvases
}
SHIM_WORDS = 18
EXPECTED_HELPER_SIZE = SHIM_WORDS * 4


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def shim_bytes() -> bytes:
    code=(
        _mips_i(0x09,29,29,-16),           # addiu sp,sp,-16
        _mips_i(0x3F,29,31,0),             # sd ra,0(sp), preserve parent link
        _mips_i(0x0F,0,8,0x41A0),          # lui t0,20.0f X accepted
        _mips_mtc1(8,12),                 # mtc1 t0,f12
        _mips_i(0x04,16,0,4),             # beq s0,zero,idx9: speaker
        0,                                # delay slot
        _mips_i(0x0F,0,8,0x4396),          # body Y=300.0f
        _mips_i(0x04,0,0,2),              # beq zero,zero,idx10
        0,                                # delay
        _mips_i(0x0F,0,8,0x438A),          # speaker Y=276.0f
        _mips_mtc1(8,13),                 # mtc1 t0,f13
        _mips_i(0x09,0,6,0),              # a2=0 horizontal text
        0x0C000000|((NATIVE_FONT_VA>>2)&0x03FFFFFF), # native constructor
        0,                                # delay
        _mips_i(0x37,29,31,0),            # ld ra,0(sp)
        _mips_i(0x09,29,29,16),           # addiu sp,sp,16
        0x03E00008,                       # jr ra
        0,
    )
    assert len(code)==SHIM_WORDS
    return b"".join(struct.pack("<I",word) for word in code)


def append_history_layout(approved_r67: bytes) -> tuple[bytes, dict]:
    if sha(approved_r67)!=EXPECTED_INPUT_SHA:
        raise ValueError("Unexpected r67 Help/inspection stage")
    _,fo,va,_,size,reserve,flags,_=struct.unpack_from("<8I",approved_r67,0x54)
    if fo+size!=len(approved_r67) or va!=0x902F00 or reserve!=0x100000 or flags!=7:
        raise ValueError("r67 ELF translation PT_LOAD geometry changed")
    for off,preimage in LAYOUT_INPUTS.items():
        if struct.unpack_from("<I",approved_r67,off)[0]!=preimage:
            raise ValueError(f"Independent history constructor preimage failed {off:#x}")
    if struct.unpack_from("<I",approved_r67,JAL_FILE_OFFSET)[0]!=JAL_PREIMAGE:
        raise ValueError("History font constructor callsite no longer verified")
    result=bytearray(approved_r67)
    while len(result)&3:result.append(0)
    target=va+len(result)-fo
    if target&3 or (JAL_FILE_OFFSET+0x100000-0x80)&0xF0000000 != target&0xF0000000:
        raise ValueError("MIPS JAL target not reachable")
    result.extend(shim_bytes())
    struct.pack_into("<I",result,JAL_FILE_OFFSET,0x0C000000|((target>>2)&0x03FFFFFF))
    struct.pack_into("<I",result,0x64,len(result)-fo)
    if len(result)-fo>reserve:raise ValueError("Not enough translation segment RAM")
    allowed=set(range(0x64,0x68))|set(range(JAL_FILE_OFFSET,JAL_FILE_OFFSET+4))
    for off,(a,b) in enumerate(zip(approved_r67,result)):
        if a!=b and off not in allowed:
            raise ValueError(f"Unrelated approved executable byte changed: {off:#x}")
    return bytes(result),dict(
        owner="Start-key two-canvas dialogue font creation",
        target_va=target,source_jal=JAL_FILE_OFFSET,
        new_orientation="horizontal",speaker_xy=(20,276),body_xy=(20,300),
        helper_bytes=EXPECTED_HELPER_SIZE,previous_sha256=sha(approved_r67),
        candidate_sha256=sha(result),previous_size=len(approved_r67),candidate_size=len(result),
        caveat="Static owner inference: requires PCSX2 confirmation before approval",
    )


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():raise FileExistsError("Refusing overwrite")
    output,report=append_history_layout(a.baseline.read_bytes())
    a.output.write_bytes(output)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(report)


if __name__=="__main__":
    main()
