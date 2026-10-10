"""67.05: move native H.A.N.T. icon captions onto their actual sprite rows.

This does not claim fixes to unidentified history or story-comment renderers.
Change-target label is contextually abbreviated rather than hidden offscreen.
All other accepted PS2 UI owners and save identifiers remain untouched.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
from tools.localization import encode_ps2_english
from tools.first_save_help import _icon_reservations, _metadata, _MAX_CELLS

BASE_SHA = "202857c06918bd5e4f96ea22c4b3480263c429021c57d88a36a145994da64c83"
ROTATE_SLOT = 0x596CD0
ROTATE_LENGTH = 32
PREVIOUS = "Change target"
VISIBLE = "Target"  # L1/R1 + Target: complete instruction on original fixed line
HANT_ROWS = (
    "Basic Attack", "",
    "1. Approach the enemy.", "",
    "2. Ready a weapon.",
    "Press          to equip.",     # controller icon at cells 6..14
    "3. Aim at the enemy.",
    "Use the R Stick to aim.",
    "        Select target.",       # controller icon at 2..6
    "4. Fire your weapon.",
    "Attacks consume AP.", "",
    "5. End your turn.",
    "When AP runs out,",
    "wait until next turn.", "",
    "       End turn early.",        # formerly orphaned SELECT button
    "even with AP remaining.", "",
    "     AP reminder:",            # formerly orphaned (!) icon
    "Each action uses AP.", "",
)

def sha(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def enc(text:str)->bytes:
    return encode_ps2_english(text,collapse_spaces=False)+b"\0"

def segment_offset(data:bytes,virtual:int)->int:
    base,va=struct.unpack_from("<II",data,0x58)
    idx=base+virtual-va
    if idx<base or idx>=len(data):
        raise ValueError("Bad translation pointer")
    return idx

def apply(pristine:bytes,base:bytes,pages:list)->tuple[bytes,dict]:
    if sha(base)!=BASE_SHA:
        raise ValueError("67.04 stage fingerprint mismatch")
    old=enc(PREVIOUS)
    if base[ROTATE_SLOT:ROTATE_SLOT+ROTATE_LENGTH]!=old.ljust(ROTATE_LENGTH,b"\0"):
        raise ValueError("Change-target original slot changed")
    if len(VISIBLE)>9 or len(enc(VISIBLE))>ROTATE_LENGTH:
        raise ValueError("Target label exceeds visual window/slot")
    result=bytearray(base)
    result[ROTATE_SLOT:ROTATE_SLOT+ROTATE_LENGTH]=enc(VISIBLE).ljust(ROTATE_LENGTH,b"\0")
    allowed=set(range(0x64,0x68)) | set(range(ROTATE_SLOT,ROTATE_SLOT+ROTATE_LENGTH))
    page=next(p for p in pages if p["key"]=="basic_attack")
    if page["rows"]!=len(HANT_ROWS):
        raise ValueError("Help row cardinality changed")
    holes,_=_icon_reservations(page,_metadata(pristine,page))
    for row,word in enumerate(HANT_ROWS):
        if len(word)>_MAX_CELLS or any(c<len(word) and word[c]!=" " for c in holes[row]):
            raise ValueError(f"Icon collision at Help row {row}")
    pointer_table=segment_offset(base,struct.unpack_from("<I",base,page["descriptor_offset"])[0])
    if struct.unpack_from("<I",base,pointer_table+22*4)[0]!=0x795FBC:
        raise ValueError("Help end sentinel drifted")
    edits=[]
    for row,word in enumerate(HANT_ROWS):
        if row==15 or row==18 or row==21:
            if struct.unpack_from("<I",base,pointer_table+row*4)[0]!=0x795FB8:
                raise ValueError("Help native spacer overwritten")
            continue
        pos=pointer_table+row*4
        prior_virtual=struct.unpack_from("<I",base,pos)[0]
        if row in (16,17,19,20):
            if prior_virtual!=0x795FB8:
                raise ValueError("Expected blank native icon row")
        else:
            if prior_virtual<0x902F00:
                raise ValueError("Original Help row moved unexpectedly")
        if len(result)%2:
            result.append(0)
        fo,va=struct.unpack_from("<II",base,0x58)
        target_va=va+len(result)-fo
        result.extend(enc(word))
        struct.pack_into("<I",result,pos,target_va)
        allowed.update(range(pos,pos+4))
        edits.append(dict(row=row,caption=word,owner=hex(pos)))
    if result[pointer_table+22*4:pointer_table+23*4]!=base[pointer_table+22*4:pointer_table+23*4]:
        raise ValueError("Help EOF modified")
    for page_name in ("turn_based_combat","entering_battle"):
        other=next(p for p in pages if p["key"]==page_name)
        for name in ("descriptor_offset","metadata_descriptor_offset"):
            idx=other[name]
            if result[idx:idx+4]!=base[idx:idx+4]:
                raise ValueError(f"Frozen {page_name} metadata modified")
        off=segment_offset(base,struct.unpack_from("<I",base,other["descriptor_offset"])[0])
        if result[off:off+(other["rows"]+1)*4]!=base[off:off+(other["rows"]+1)*4]:
            raise ValueError(f"Frozen {page_name} content modified")
    fo=struct.unpack_from("<I",base,0x58)[0]
    if fo+struct.unpack_from("<I",base,0x64)[0]!=len(base):
        raise ValueError("PT_LOAD geometry changed")
    if len(result)-fo>struct.unpack_from("<I",base,0x68)[0]:
        raise ValueError("PT_LOAD reserve exceeded")
    struct.pack_into("<I",result,0x64,len(result)-fo)
    for offset,(previous,updated) in enumerate(zip(base,result)):
        if previous!=updated and offset not in allowed:
            raise ValueError(f"Unowned bytes at {offset:#x}")
    return bytes(result),dict(
        prior_sha256=sha(base),sha256=sha(result),
        previous_size=len(base),new_size=len(result),
        appended_bytes=len(result)-len(base),
        fixed_slot=[ROTATE_SLOT,ROTATE_LENGTH,VISIBLE],
        basic_attack_rows=edits,
        approved_pedestal_locked=True,approved_turn_based_combat_locked=True,
        geometric_renderer_changes=False,save_namespace_modified=False,
        unresolved=[
            "START-key dialogue log remains vertical (actual owner not proven)",
            "Chamber entry companion text and blue background overflow",
            "Lion Statue item pickup label overflow (correct official name retained)",
        ],
    )
def main():
    ap=argparse.ArgumentParser()
    for field in ("pristine","baseline","manifest","output","report"):
        ap.add_argument("--"+field,type=Path,required=True)
    args=ap.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("Output already exists")
    pages=json.loads(args.manifest.read_text())["pages"]
    result,report=apply(args.pristine.read_bytes(),args.baseline.read_bytes(),pages)
    args.output.write_bytes(result)
    args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print({k:v for k,v in report.items() if k!="basic_attack_rows"})
if __name__=="__main__":
    main()
