"""r67.14s Lion Statue title final 0.78 -> 0.72 horizontal fit.

Only change the approved item-ID-413-private helper's two instruction
immediates. No global text owner, object layout, sprite geometry, name string,
save data or other UI changes. Derived from the preserved r67.14r diagnostic;
r67.14q remains the immutable approved baseline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO, ELF_SEGMENT_VA, ELF_SEGMENT_RESERVE, ELF_BIAS
from tools.r67_lion_statue_ui import sha, item_pointer, CALL_SITES, _jal, make_helper, NATIVE_XY_SCALING_SETTER
from tools.r67_14q_approved_lock import MANIFEST, verify_approved

SOURCE_R_SHA256="55c7a2041909d22f1fb109d280c75b6e29cdad6cf3531626401409242245091c"
SOURCE_SCALE=0.78
TARGET_SCALE=0.72
PRIVATE_HELPER_VA=0x963FD0
SCALE_LOAD_HI_VA=0x96400C
SCALE_LOAD_LO_VA=0x964010

def word_for_float(f:float)->int:
    return struct.unpack("<I",struct.pack("<f",f))[0]

def apply(source:bytes)->tuple[bytes,dict]:
    if sha(source)!=SOURCE_R_SHA256:
        raise ValueError("Expected exact r67.14r input fingerprint")
    fo,va,size,reserve=(struct.unpack_from("<I",source,i)[0] for i in (0x58,0x5c,0x64,0x68))
    if (fo,va,fo+size,reserve)!=(ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(source),ELF_SEGMENT_RESERVE):
        raise ValueError("Unexpected ELF PT_LOAD layout")
    item_ptr=item_pointer(source)
    helper=make_helper(item_ptr)
    off=fo+PRIVATE_HELPER_VA-va
    if source[off:off+len(helper)]!=helper:
        raise ValueError("Original item-specific helper differs")
    for site in CALL_SITES:
        if struct.unpack_from("<I",source,site-ELF_BIAS)[0]!=_jal(PRIVATE_HELPER_VA):
            raise ValueError(f"Lion name interception no longer installed: {site:#x}")
    before=word_for_float(SOURCE_SCALE);after=word_for_float(TARGET_SCALE)
    new=bytearray(source)
    for addr,oldw,neww in (
        (SCALE_LOAD_HI_VA,0x3c080000|(before>>16),0x3c080000|(after>>16)),
        (SCALE_LOAD_LO_VA,0x35080000|(before&0xffff),0x35080000|(after&0xffff))
    ):
        p=fo+addr-va
        if struct.unpack_from("<I",source,p)[0]!=oldw:
            raise ValueError(f"Exact r67.14r scale-preimage drift at {addr:#x}")
        struct.pack_into("<I",new,p,neww)
    allowed={o for addr in (SCALE_LOAD_HI_VA,SCALE_LOAD_LO_VA)
             for o in range(fo+addr-va,fo+addr-va+4)}
    changed=[i for i,(a,b) in enumerate(zip(source,new)) if a!=b]
    if not changed or not set(changed)<=allowed:
        raise ValueError("Unexpected non-item byte mutation")
    verify_approved(bytes(new),json.loads(MANIFEST.read_text()))
    return bytes(new),{
        "revision":"r67.14s","status":"DIAGNOSTIC_PENDING_USER_VISUAL_APPROVAL",
        "r67_14r_elf_sha256":SOURCE_R_SHA256,"r67_14s_elf_sha256":sha(new),
        "scale_before":SOURCE_SCALE,"scale_after":TARGET_SCALE,
        "horizontal_only":True,"item_string":"Lion Statue",
        "native_item_id":413,"patched_code_vas":[hex(SCALE_LOAD_HI_VA),hex(SCALE_LOAD_LO_VA)],
        "modified_existing_offsets":[hex(x) for x in changed],
        "approved_r67_14q_lock_passed":True,"save_logic_unchanged":True,
        "runtime_verified":False,"release_approved":False
    }

def main():
    p=argparse.ArgumentParser()
    for field in ("input","output","report"):p.add_argument("--"+field,required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():raise FileExistsError("Never overwrite candidate")
    elf,report=apply(a.input.read_bytes())
    a.output.write_bytes(elf)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":main()
