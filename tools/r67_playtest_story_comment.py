"""Conservative official-English semantically equivalent native story-comment width fix.

The first-dungeon story comment used 22 full-width glyphs, extending past its
green bubble. This is a separate proven owner, NOT companion AFK or L1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.localization import encode_ps2_english


OWNER = 0x3D3428
SOURCE = 0x3C1A50
OFFICIAL = "What an eerie place..."
COMPACT = "An eerie place..."
SOURCE_JP = "不気味な場所じゃのう…。"

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def append_compact_story_comment(pristine: bytes, approved: bytes) -> tuple[bytes, dict]:
    expected=SOURCE_JP.encode("cp932")+b"\x00"
    if pristine[SOURCE:SOURCE+len(expected)]!=expected:
        raise ValueError("Story comment Japanese preimage mismatch")
    if not len(COMPACT)<len(OFFICIAL) or len(COMPACT)>17:
        raise ValueError("Story comment exceeds native 17-cell bound")
    tp, fo, va, _pa, size, reserve, flags, align=struct.unpack_from("<8I",approved,0x54)
    if tp!=1 or flags!=7 or align!=16 or fo+size!=len(approved) or reserve!=0x100000:
        raise ValueError("Translation segment changed")
    old_va=struct.unpack_from("<I",approved,OWNER)[0]
    original=encode_ps2_english(OFFICIAL,collapse_spaces=False)+b"\0"
    old=fo+old_va-va
    if approved[old:old+len(original)]!=original:
        raise ValueError("Official PS4 comment not present at exact owner")
    output=bytearray(approved)
    if len(output)%2: output.append(0)
    new_va=va+len(output)-fo
    output.extend(encode_ps2_english(COMPACT,collapse_spaces=False)+b"\0")
    struct.pack_into("<I",output,OWNER,new_va)
    struct.pack_into("<I",output,0x64,len(output)-fo)
    if len(output)-fo>reserve: raise ValueError("Appended text exceeds mapped RAM")
    allowed=set(range(0x64,0x68))|set(range(OWNER,OWNER+4))
    if any(a!=b and i not in allowed for i,(a,b) in enumerate(zip(approved,output))):
        raise ValueError("Unexpected non-owner modified")
    return bytes(output),dict(source_jp=SOURCE_JP,official=OFFICIAL,
        compact=COMPACT,source_offset=SOURCE,pointer_offset=OWNER,
        old_target_va=old_va,new_target_va=new_va,
        original_sha256=sha(approved),new_sha256=sha(output),
        original_size=len(approved),new_size=len(output))

def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ("pristine","baseline","output","report"):
        ap.add_argument("--"+name,required=True,type=Path)
    a=ap.parse_args()
    if a.output.exists() or a.report.exists():
        raise FileExistsError("Refusing output overwrite")
    payload,report=append_compact_story_comment(a.pristine.read_bytes(),a.baseline.read_bytes())
    a.output.write_bytes(payload)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(report)

if __name__=="__main__":
    main()
