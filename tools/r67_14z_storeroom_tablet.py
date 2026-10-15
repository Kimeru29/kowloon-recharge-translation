"""r67.14z — exact-owned Storeroom room label and three-row inscription.

Derived only from the visually approved SHA-pinned r67.14y staged ELF. The
original q/t/y UI code, event lifecycle, all object/save text, save atlas,
H.A.N.T., fonts and original save metadata are immutable. Allowed changes:
two room-name pointer words; three Stone-tablet inscription pointer words;
PT_LOAD.p_filesz; append-only two-byte-aligned English strings.

The PS4 English corpus proves "Storeroom" and the original three inscription
sentences. The inscription is semantically compacted to fit all native row
slots with original CP932 quote/indentation glyphs retained.
"""
from __future__ import annotations
import hashlib
import json
import struct
from pathlib import Path

from tools.inspect_english_bytes import parse as parse_english
from tools.localization import encode_ps2_english
from tools.r67_14t_stone_tablet_fit import (
    read_string, assert_all_tablets_fit, MAX_GLYPH_CELLS,
)
from tools.r67_14q_approved_lock import verify_approved, MANIFEST as Q
from tools.r67_14t_approved_ui_lock import verify_ui, MANIFEST as T
from tools.r67_14y_inspection_save import validate_result as validate_y_inspections
from tools.r67_14y_release import verify_save_identity

ROOT=Path(__file__).resolve().parents[1]
CORPUS=Path("/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes")
CORPUS_SHA="b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b"
Y_STAGE_SHA="73c27c2728609c7ee38f9c21cfcbc1a26ca980dc8b45b19383d64677c8eba369"
Y_INSTALLED_SHA="e11997c7b344cfb811497aa8c3bbaef86059a4e40911585f26442ff7a92ebf8d"
Y_ISO_SHA="079b4d0ed73fb010b0d0020f5a3e84357b44804a9b2a2425fa3328fd497aee8f"
FO=0x803150
VA=0x902F00
RESERVE=0x100000
ROOM_SOURCE_PTR=0x6CC6E0
ROOM_OWNERS=(0x5CD6B4,0x5CD84C)
ROOM_JP="資材庫（しざいこ）"
ROOM_EN="Storeroom"
ROOM_OFFICIAL_OFFSET=0xC30FA
TABLET_RECORD=0x591090
TABLET_POINTERS=(0x690F90,0x690FC0,0x690FE0)
TABLET_OWNERS=(0x591098,0x59109C,0x5910A0)
# Exact original indentation and special CP932 punctuation remain native.
TABLET_PREFIXES=(b"\x81\x40\x81\x68",b"\x81\x40\x81\x40",b"\x81\x40\x81\x40")
TABLET_SUFFIXES=(b"",b"",b"\x81\x68")
TABLET_JP=(
    "　”《２つ》の水が《１つ》へと変わる時、",
    "　　その力の前に、",
    "　　《黄金の鎖》は消え去らん。”",
)
TABLET_TEXT=(
    "When 2 waters join,",
    "their power dispels",
    "the golden lock.",
)
TABLET_OFFICIAL_OFFSETS=(0xCC573,0xCC5D5,0xCC612)


def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def verify_official()->list[dict]:
    if not CORPUS.is_file() or sha(CORPUS.read_bytes())!=CORPUS_SHA:
        raise ValueError("Official PS4 English corpus missing or changed")
    by_offset={off:(jp,en) for jp,en,off in parse_english(CORPUS)}
    evidence=[]
    checks=((ROOM_OFFICIAL_OFFSET,ROOM_JP,ROOM_EN),)+tuple(
        (off,jp,None) for off,jp in zip(TABLET_OFFICIAL_OFFSETS,TABLET_JP,strict=True))
    for off,jp,expected in checks:
        if off not in by_offset or by_offset[off][0]!=jp:
            raise ValueError(f"Official PS4 source phrase mismatch {off:#x}")
        en=by_offset[off][1]
        if expected is not None and en!=expected:
            raise ValueError(f"Official PS4 translated room name mismatch {off:#x}")
        evidence.append({"ps4_offset":hex(off),"japanese":jp,"official":en})
    return evidence


def _validate_header(elf:bytes):
    if sha(elf)!=Y_STAGE_SHA:
        raise ValueError("Only exact approved r67.14y staged ELF is accepted")
    header=struct.unpack_from("<8I",elf,0x54)
    if (header[0],header[1],header[2],header[4]+header[1],header[5],header[6],header[7])!=(
        1,FO,VA,len(elf),RESERVE,7,16
    ):
        raise ValueError("ELF translation PT_LOAD preimage drift")
    if struct.unpack_from("<6I",elf,TABLET_RECORD)!=(
        0x962C7A,0x962D3C,*TABLET_POINTERS,0x962C94
    ):
        raise ValueError("Storeroom Stone tablet six-field record changed")
    for owner in ROOM_OWNERS:
        if struct.unpack_from("<I",elf,owner)[0]!=ROOM_SOURCE_PTR:
            raise ValueError(f"Storeroom room pointer owner drift at {owner:#x}")
    if read_string(elf,ROOM_SOURCE_PTR).decode("cp932")!=ROOM_JP:
        raise ValueError("Original Storeroom Japanese name drift")
    for i,ptr in enumerate(TABLET_POINTERS):
        data=read_string(elf,ptr)
        if data.decode("cp932")!=TABLET_JP[i]:
            raise ValueError(f"Native inscription row {i} source drift")
        if not data.startswith(TABLET_PREFIXES[i]) or not data.endswith(TABLET_SUFFIXES[i]):
            raise ValueError(f"Native inscription punctuation/indent drift at row {i}")
    verify_approved(elf,json.loads(Q.read_text()))
    verify_ui(elf,json.loads(T.read_text()))
    validate_y_inspections(elf)
    verify_save_identity(elf)


def expected_writes(source:bytes)->tuple[bytes,dict]:
    _validate_header(source)
    evidence=verify_official()
    out=bytearray(source)
    records=[]
    changed_owners={}
    for key,owners,text in (
        ("room_storeroom",ROOM_OWNERS,encode_ps2_english(ROOM_EN,collapse_spaces=False)),
        *(
            (f"storeroom_tablet_row_{i}",(owner,),
             TABLET_PREFIXES[i]+encode_ps2_english(TABLET_TEXT[i],collapse_spaces=False)+TABLET_SUFFIXES[i])
            for i,owner in enumerate(TABLET_OWNERS)
        )
    ):
        if len(out)&1:out.append(0)
        new_va=VA+len(out)-FO
        if new_va&1:raise ValueError("Translation text not half-word aligned")
        out.extend(text+b"\0")
        for off in owners:
            changed_owners[off]=new_va
            struct.pack_into("<I",out,off,new_va)
        cells=len(text.decode("cp932"))
        if key.startswith("storeroom_tablet_") and cells>MAX_GLYPH_CELLS:
            raise ValueError(f"Inscription row would overflow: {key} has {cells} cells")
        records.append({"owner":key,"pointers":[hex(x) for x in owners],
                        "new_va":hex(new_va),"text":text.decode("cp932"),
                        "full_width_cells":cells,"byte_sha256":sha(text+b"\0")})
    if len(out)-FO>RESERVE:
        raise ValueError("Translation segment exceeds native 1MiB reservation")
    struct.pack_into("<I",out,0x64,len(out)-FO)
    changed=[p for p,(a,b) in enumerate(zip(source,out)) if a!=b]
    allowed=set(range(0x64,0x68))
    for owner in changed_owners:allowed.update(range(owner,owner+4))
    if not changed or set(changed)-allowed:
        raise ValueError(f"Unauthorized alteration of previously approved y ELF: {set(changed)-allowed}")
    result=bytes(out)
    fit=assert_all_tablets_fit(result)
    if fit["registered_tablets"]!=58 or fit["populated_tablet_rows"]!=160:
        raise ValueError("Other tablets changed")
    verify_approved(result,json.loads(Q.read_text()))
    verify_ui(result,json.loads(T.read_text()))
    validate_y_inspections(result)
    verify_save_identity(result)
    return result,{
        "revision":"r67.14z",
        "status":"DIAGNOSTIC_USER_SCREENSHOT_APPROVAL_PENDING",
        "approved_y_staged_sha256":Y_STAGE_SHA,
        "candidate_staged_elf_sha256":sha(result),
        "official_ps4_corpus_sha256":CORPUS_SHA,
        "official_source_evidence":evidence,
        "changed_pointer_owners":list(map(hex,sorted(changed_owners))),
        "modified_original_offsets":list(map(hex,changed)),
        "appended_bytes":len(result)-len(source),
        "owned_strings":records,
        "global_tablet_width_gate":fit,
        "unchanged_previous_q_t_y_owners":True,
        "original_save_and_event_routines_unchanged":True,
        "pixel_fit_runtime_confirmed":False,
        "approved_for_main":False
    }


def main():
    import argparse
    ap=argparse.ArgumentParser()
    for n in ("input","output","report"):ap.add_argument("--"+n,type=Path,required=True)
    args=ap.parse_args()
    if args.output.exists() or args.report.exists():raise FileExistsError("No candidate overwrite permitted")
    data,report=expected_writes(args.input.read_bytes())
    args.output.write_bytes(data)
    args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("official_source_evidence","owned_strings")},sort_keys=True))


if __name__=="__main__":main()
