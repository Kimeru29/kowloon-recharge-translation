"""r67.02 bounded first-dungeon inspection and H.A.N.T. text reflow.

All new ownership is checked against the original Japanese executable and the
official PS4 English corpus, with the 67.01 entire-ELF preimage pinned.
No renderer code, r66 AFK/L1, Help icon metadata or save identity is touched.
"""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, struct
from collections import defaultdict
from tools.localization import encode_ps2_english
from tools.inspect_english_bytes import parse
from tools.first_save_help import _icon_reservations, _metadata, _MAX_CELLS
from tools.companion_hud_data import COMPANION_COMMENT_DATA

BASE_SHA = "4f5f01f0a293172c6ebfa81f311f5d1bc8df6cb3e3a15dd17ce279ab47e47798"
# For previously translated strings, source pointers in 67.01 are re-pointed to
# shorter bounded captions. Alias roles remain unchanged.
INSPECTIONS = {
    0x590BE0: "Opens and closes.",
    0x590D00: "Sturdy door.",
    0x590D80: "Stores valuables.",
    0x695DC0: "Door",
    0x695DC8: "",
    0x695C28: "Stone tablet",
    0x695C30: "",
    0x590DC0: "",
    0x58AC88: "Stone Pedestal",
    0x58ACA0: "Carved stone base.",
    0x58ACC0: "",
    0x695C48: "Large Container",
    0x58B560: "Sturdy vase.",
    0x58B580: "Movement inside.",
    0x58B5A0: "",
}
# The 67.01 formerly long tablet rows are proven official PS4 owners.
TABLET_KEYS = {
    "object_ancient_writing_description": "Egyptian writing.",
    "lion_inscription_1": "Four beasts face off.",
    "lion_inscription_2": "East door opens.",
}
STORY_COMMENTS = {
    0x3C1A50: "Eerie place.",
    0x3C1F38: "Door's ready.",
}
FIXED_PICKUP = {
    0x596010: "Stone",
    0x596028: "carving.",
}
# Preserve native Help row cardinality/EOF and the last seven blank control
# rows; ONLY the 15 existing populated Basic Attack entries are redirected.
BASIC_ATTACK = (
    "Basic Attack",
    "",
    "1. Approach an enemy.",
    "",
    "2. Equip your weapon.",
    "               Equip.",
    "3. Aim at an enemy.",
    "Use the R Stick to aim.",
    "       Point at the enemy.",
    "4. Fire the ready weapon.",
    "Attacking consumes AP.",
    "",
    "5. End your turn.",
    "When AP is depleted,",
    "you cannot act this turn.",
)

def sha(blob:bytes)->str: return hashlib.sha256(blob).hexdigest()

def apply(pristine:bytes,base:bytes,official_rows:list[tuple[str,str,int]],help_pages:list[dict],original_owners:list[dict])->tuple[bytes,dict]:
    if sha(base)!=BASE_SHA: raise ValueError("67.01 executable fingerprint mismatch")
    _type,fo,va,_p,size,reserve,flags,align=struct.unpack_from("<8I",base,0x54)
    if _type!=1 or fo+size!=len(base) or reserve!=0x100000 or flags!=7 or align!=16:
        raise ValueError("Unexpected PT_LOAD layout")
    official=defaultdict(set)
    for jp,en,_ in official_rows: official[jp].add(en)
    output=bytearray(base)
    changes=[];allowed=set(range(0x64,0x68))
    def append(text:str)->int:
        if len(output)&1:output.append(0)
        ptr=va+len(output)-fo
        output.extend(encode_ps2_english(text,collapse_spaces=False)+b"\0")
        return ptr
    def aliases(offset:int)->list[int]:
        needle=struct.pack("<I",0x100000+offset-0x80)
        return [i for i in range(0,len(pristine)-4,4) if pristine[i:i+4]==needle]
    def patch(name:str,owners:list[int],text:str,limit:int=22):
        if len(text)>limit:raise ValueError(f"Overflow risk {name}: {text}")
        if not owners:raise ValueError(f"No aliases for {name}")
        old_values={struct.unpack_from("<I",base,i)[0] for i in owners}
        if len(old_values)!=1:raise ValueError(f"Alias-target mismatch {name}")
        old=old_values.pop()
        dest=append(text)
        for off in owners:
            struct.pack_into("<I",output,off,dest)
            allowed.update(range(off,off+4))
        changes.append(dict(name=name,alias_count=len(owners),pointer_offsets=owners,old_va=old,new_va=dest,english=text))
    for offset,text in INSPECTIONS.items():
        z=pristine.find(b"\0",offset,offset+150)
        jp=pristine[offset:z].decode("cp932")
        en=official[jp]
        if len(en)!=1:raise ValueError(f"Official PS4 owner ambiguous {offset:#x}: {en}")
        if not (text==next(iter(en)) or text=="" or len(text)<len(next(iter(en))) or text=="Stone Pedestal"):
            raise ValueError(f"Unexpected nonofficial variant {offset:#x}")
        if text=="" and (next(iter(en))!="@D" and offset not in (0x695DC8,0x590DC0)):
            raise ValueError("Unapproved blank phonetic")
        patch(f"inspection_{offset:x}",aliases(offset),text)
    for key,text in TABLET_KEYS.items():
        owner=next(o for o in original_owners if o["key"]==key)
        jp_pos=owner["source_offset"]
        jp=pristine[jp_pos:pristine.find(b"\0",jp_pos,jp_pos+150)].decode("cp932")
        if owner["official_english"] not in official[jp]:raise ValueError(f"Official tablet mismatch {key}")
        patch(key,owner["owner_offsets"],text,22)
    for source,text in STORY_COMMENTS.items():
        record=next((r for r in COMPANION_COMMENT_DATA if r[0]==source),None)
        if record is None:raise ValueError(f"Unknown companion source {source:#x}")
        addr,jp,english,_ps4,owners=record
        if english not in official[jp]:raise ValueError(f"Companion source not in PS4 corpus {source:#x}")
        if len(text)>14: raise ValueError(f"Story bubble too narrow: {text}")
        # These are separate story comments, not r66 AFK bubble records.
        patch(f"comment_{source:x}",list(owners),text,14)
    for off,text in FIXED_PICKUP.items():
        for item in (text,):
            data=encode_ps2_english(item,collapse_spaces=False)+b"\0"
            if len(data)>24:raise ValueError("Fixed pickup slot overrun")
            if off==0x596010:
                expected=encode_ps2_english("Stone lion")+b"\0"
            else:expected=encode_ps2_english("  statue.")+b"\0"
            if not base[off:off+24].startswith(expected):raise ValueError("Pickup 67.01 bytes changed")
            output[off:off+24]=data.ljust(24,b"\0")
            allowed.update(range(off,off+24))
            changes.append(dict(name=f"pickup_{off:x}",pointer_offsets=[off],english=text))
    page=next(p for p in help_pages if p["key"]=="basic_attack")
    rows=page["rows"];assert rows==22 and len(BASIC_ATTACK)==15
    reserved,_=_icon_reservations(page,_metadata(pristine,page))
    for row,line in enumerate(BASIC_ATTACK):
        if len(line)>_MAX_CELLS: raise ValueError(f"Basic Help line too long: {row}")
        if any(x<len(line) and line[x]!=" " for x in reserved[row]):
            raise ValueError(f"Basic Help icon overlap: row {row}")
    desc=page["descriptor_offset"]
    old_table=struct.unpack_from("<I",base,desc)[0]
    table=fo+old_table-va
    basic_ptr_offsets=[]
    for row,line in enumerate(BASIC_ATTACK):
        ptr_at=table+row*4
        basic_ptr_offsets.append(ptr_at)
        old=struct.unpack_from("<I",base,ptr_at)[0]
        if old in (0xffffffff,0xfffffffe):raise ValueError(f"Missing original Basic Help row {row}")
        new=append(line)
        struct.pack_into("<I",output,ptr_at,new)
        allowed.update(range(ptr_at,ptr_at+4))
    # Controller-only rows 15-21, EOF, page descriptor, and ALL metadata remain byte identical.
    if output[table+60:table+(rows+1)*4]!=base[table+60:table+(rows+1)*4]:
        raise ValueError("Altered original Basic Help blank rows/EOF")
    for locked in ("entering_battle","turn_based_combat"):
        p=next(x for x in help_pages if x["key"]==locked)
        t=struct.unpack_from("<I",base,p["descriptor_offset"])[0]
        off=fo+t-va
        length=(p["rows"]+1)*4
        if output[off:off+length]!=base[off:off+length]:
            raise ValueError(f"Locked H.A.N.T. table modified: {locked}")
    struct.pack_into("<I",output,0x64,len(output)-fo)
    if len(output)-fo>reserve:raise ValueError("Appended text RAM exhausted")
    for i,(a,b) in enumerate(zip(base,output)):
        if a!=b and i not in allowed:raise ValueError(f"Unknown executable diff {i:#x}")
    return bytes(output),dict(changes=changes,modified_existing_bytes=len(allowed),
        appended_bytes=len(output)-len(base),expected_previous_sha=sha(base),
        sha256=sha(output),prior_length=len(base),new_length=len(output),
        help_rows=len(BASIC_ATTACK),basic_pointer_offsets=basic_ptr_offsets,
        basic_descriptor_offset=desc)

def main():
    p=argparse.ArgumentParser()
    for k in ("pristine","base","official","help-manifest","original-owner-manifest","output","report"):
        p.add_argument("--"+k,type=Path,required=True)
    x=p.parse_args()
    if x.output.exists() or x.report.exists():raise FileExistsError("Refusing overwrite")
    elf,report=apply(x.pristine.read_bytes(),x.base.read_bytes(),parse(x.official),
        json.loads(x.help_manifest.read_text())["pages"],
        json.loads(x.original_owner_manifest.read_text())["owners"])
    x.output.write_bytes(elf);x.report.write_text(json.dumps(report,indent=2)+"\n")
    print("67.02 owners",len(report["changes"]),"append",report["appended_bytes"],"hash",report["sha256"])

if __name__=="__main__":main()
