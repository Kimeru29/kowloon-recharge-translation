"""Generic r67 stone-tablet text-fit enforcement for all 58 native records.

Discover the complete game-wide Stone tablet object class by its shared exact
translated title pointer, validate EVERY populated inscription row against
the original maximum 21 full-width PS2 glyph cells and preserve each record's
row count, title and header. Two existing early-game remaster translations
are too long; replace their six rows with bounded semantic equivalents,
retaining original PS2 indentation and special quote-marker bytes.

This is a game-wide translation-time invariant, not a claim that the native
runtime renderer auto-scales future, unknown record types. Fail closed when a
future translation exceeds native width or the registered tablet class drifts.
"""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
from tools.localization import encode_ps2_english
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO,ELF_SEGMENT_VA,ELF_SEGMENT_RESERVE
from tools.r67_lion_statue_ui import sha
from tools.r67_14q_approved_lock import MANIFEST,verify_approved

SOURCE_S_SHA256="c167414d568b910572474436c9726915299275d37b9f56d27afc4a69f61fbb18"
TITLE_POINTER=0x962C7A
EMPTY_ROW_POINTER=0x795B9C
TABLET_RECORDS=58
MAX_GLYPH_CELLS=21
EXPECTED_POPULATED_INSCRIPTION_ROWS=160
# Every current tablet has an identical registered title and 5 textual fields;
# rows 2, 3, 4 are the inscription body (the other fields are name/description).
TABLET_SCANNED_SPAN=(0x580000,0x600000)

# Native scripts already reserve leading double-byte spaces and the special
# 0xEEFC quotation glyph. These MUST remain, not be replaced with ASCII quotes.
# Each replacement only stores bounded text inside the original row.
COMPACT_INSCRIPTION_TEXT={
    0x590F38:"Nether gods face",
    0x590F3C:"south at sunrise;",
    0x590F40:"heaven's isle rises",
    0x590FB8:"The bowed one",
    0x590FBC:"walks west, finds",
    0x590FC0:"the mercy of God.",
}
PREFIX={
    0x590F38:b"\x81\x40\xee\xfc",
    0x590F3C:b"\x81\x40\x81\x40",
    0x590F40:b"\x81\x40",
    0x590FB8:b"\x81\x40\xee\xfc",
    0x590FBC:b"\x81\x40\x81\x40",
    0x590FC0:b"\x81\x40",
}
SUFFIX={0x590F40:b"\xee\xfc",0x590FC0:b"\xee\xfc"}


def resolve_pointer(raw:bytes,ptr:int)->int:
    # Native original main image as well as appended English text are valid.
    pos=(ELF_SEGMENT_FO+ptr-ELF_SEGMENT_VA) if ptr>=ELF_SEGMENT_VA else (ptr-0xfff80)
    if not 0<=pos<len(raw):raise ValueError(f"Inscription pointer out of range: {ptr:#x}")
    return pos


def read_string(raw:bytes,ptr:int)->bytes:
    pos=resolve_pointer(raw,ptr)
    end=raw.find(b"\0",pos,pos+256)
    if end<0:raise ValueError(f"Tablet inscription missing terminating NUL: {ptr:#x}")
    return raw[pos:end]


def tablet_registry(raw:bytes)->list[int]:
    needle=struct.pack("<I",TITLE_POINTER)
    found:list[int]=[]
    start,end=TABLET_SCANNED_SPAN
    pos=start
    while True:
        pos=raw.find(needle,pos,end)
        if pos<0:break
        if pos%4==0:
            found.append(pos)
        pos+=4
    if len(found)!=TABLET_RECORDS:
        raise ValueError(f"Tablet registry drift: expected 58 found {len(found)}")
    return found


def tablet_rows(raw:bytes)->list[dict]:
    rows=[]
    for record in tablet_registry(raw):
        values=struct.unpack_from("<6I",raw,record)
        if values[0]!=TITLE_POINTER or values[5] != 0x962C94:
            raise ValueError(f"Unexpected stone-tablet object record schema {record:#x}")
        if not read_string(raw,values[1]):
            raise ValueError(f"Tablet description missing at {record:#x}")
        for index in (2,3,4):
            ptr=values[index]
            if ptr==EMPTY_ROW_POINTER:continue
            data=read_string(raw,ptr)
            if not data:continue
            try:text=data.decode("cp932")
            except UnicodeDecodeError as exc:raise ValueError(f"Corrupt tablet text at {record:#x}:{index}") from exc
            if not text.strip():continue  # native one-cell padding/sentinel is not inscription text
            rows.append(dict(record_offset=record,row_index=index,ptr=ptr,cell_count=len(text),text=text))
    if len(rows)!=EXPECTED_POPULATED_INSCRIPTION_ROWS:
        raise ValueError(f"Stone-tablet row cardinality changed: {len(rows)}")
    return rows


def assert_all_tablets_fit(raw:bytes)->dict:
    rows=tablet_rows(raw)
    errors=[r for r in rows if r["cell_count"]>MAX_GLYPH_CELLS]
    if errors:
        raise ValueError("Oversized stone tablet rows: "+", ".join(
            f"{r['record_offset']:#x}/row{r['row_index']}={r['cell_count']}"
            for r in errors))
    return {
        "registered_tablets":TABLET_RECORDS,
        "populated_tablet_rows":len(rows),
        "native_max_full_width_glyphs":MAX_GLYPH_CELLS,
        "maximum_current_glyph_count":max(r["cell_count"] for r in rows),
        "overwide_rows":0,
        "all_current_game_tablet_inscriptions_within_native_row_limit":True,
    }


def replacement_at(off:int)->bytes:
    prefix=PREFIX[off]
    suffix=SUFFIX.get(off,b"")
    return prefix+encode_ps2_english(COMPACT_INSCRIPTION_TEXT[off],collapse_spaces=False)+suffix+b"\0"


def apply(source:bytes)->tuple[bytes,dict]:
    if sha(source)!=SOURCE_S_SHA256:raise ValueError("Expected exact r67.14s Lion fit source ELF")
    typ,fo,va,unused,size,reserve,flags,align=struct.unpack_from("<8I",source,0x54)
    if (typ,fo,va,fo+size,reserve,flags,align)!=(1,ELF_SEGMENT_FO,ELF_SEGMENT_VA,len(source),ELF_SEGMENT_RESERVE,7,16):
        raise ValueError("ELF segment format changed")
    original=tablet_rows(source)
    originals={r["record_offset"]+r["row_index"]*4:r for r in original}
    failures=[r for r in original if r["cell_count"]>MAX_GLYPH_CELLS]
    if {r["record_offset"]+r["row_index"]*4 for r in failures}!=set(COMPACT_INSCRIPTION_TEXT):
        raise ValueError("Overwide tablet ownership changed; not safe to auto-compact")
    output=bytearray(source)
    allowed=set(range(0x64,0x68))
    patched={}
    for off in sorted(COMPACT_INSCRIPTION_TEXT):
        old_ptr=struct.unpack_from("<I",source,off)[0]
        old_data=read_string(source,old_ptr)
        if not old_data.startswith(PREFIX[off]):
            raise ValueError(f"Native inscription quote/indent preimage changed: {off:#x}")
        if SUFFIX.get(off) and not old_data.endswith(SUFFIX[off]):
            raise ValueError(f"Native inscription end quote changed: {off:#x}")
        replacement=replacement_at(off)
        cells=len(replacement[:-1].decode("cp932"))
        if cells>MAX_GLYPH_CELLS:
            raise ValueError(f"Replacement would exceed tablet width: {off:#x} -> {cells}")
        if len(output)&1:output.append(0)
        dest=ELF_SEGMENT_VA+len(output)-ELF_SEGMENT_FO
        output.extend(replacement)
        struct.pack_into("<I",output,off,dest)
        allowed.update(range(off,off+4))
        patched[hex(off)]={
            "original_ptr":hex(old_ptr),"new_ptr":hex(dest),
            "old_cells":len(old_data.decode("cp932")),
            "new_cells":cells,
            "compact_semantics":COMPACT_INSCRIPTION_TEXT[off],
            "retains_original_indent_and_quote_markers":True,
        }
    if len(output)-fo>reserve:raise ValueError("Translation segment exceeds reserved memory")
    struct.pack_into("<I",output,0x64,len(output)-fo)
    changed={i for i,(a,b) in enumerate(zip(source,output)) if a!=b}
    if not changed or changed-allowed:raise ValueError(f"Unclassified original ELF byte modifications: {changed-allowed}")
    result=bytes(output)
    fit=assert_all_tablets_fit(result)
    verify_approved(result,json.loads(MANIFEST.read_text()))
    for record in tablet_registry(source):
        # All non-tablet-text fields and all other 56 records MUST remain unchanged.
        if record not in (0x590F30,0x590FB0):
            if result[record:record+24]!=source[record:record+24]:
                raise ValueError(f"Other tablet record was changed: {record:#x}")
        else:
            if result[record:record+8]!=source[record:record+8] or result[record+20:record+24]!=source[record+20:record+24]:
                raise ValueError("Tablet title/description/end marker changed")
    return result,{
        "revision":"r67.14t","status":"DIAGNOSTIC_PENDING_VISUAL_APPROVAL",
        "source_elf_sha256":SOURCE_S_SHA256,"candidate_elf_sha256":sha(result),
        "old_elf_size":len(source),"new_elf_size":len(result),
        "appended_bytes":len(result)-len(source),
        "patched_inscription_rows":patched,
        "modified_existing_offsets":list(map(hex,sorted(changed))),
        "gamewide_tablet_width_gate":fit,
        "approved_r67_14q_lock_passed":True,
        "save_serialization_modified":False,
        "runtime_verified":False,"release_approved":False,
    }

def main():
    from tools.r67_14q_approved_lock import extract_iso_elf
    p=argparse.ArgumentParser(description=__doc__)
    for field in ("input","output","report","check-elf","check-iso","build-report"):
        p.add_argument("--"+field,type=Path)
    a=p.parse_args()
    if a.check_elf is not None or a.check_iso is not None:
        if a.check_elf is not None and a.check_iso is not None:
            p.error("Check either an ELF or a finished ISO, not both")
        if a.check_iso is not None and a.build_report is None:
            p.error("An ISO requires its build report to locate the executable")
        if a.check_elf is not None:
            current=a.check_elf.read_bytes()
        else:
            current=extract_iso_elf(a.check_iso,json.loads(MANIFEST.read_text()),a.build_report)
        approved=verify_approved(current,json.loads(MANIFEST.read_text()))
        result={"status":"PASS_ALL_58_GAMEWIDE_STONE_TABLETS_FIT","stone_tablets":assert_all_tablets_fit(current),
                "r67_14q_lock":approved["status"]}
        if a.report is not None:
            if a.report.exists():raise FileExistsError("Existing tablet-fit gate report")
            a.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print(json.dumps(result,sort_keys=True))
        return
    if a.input is None or a.output is None or a.report is None:
        p.error("For a new candidate, provide --input, --output and --report")
    if a.output.exists() or a.report.exists():raise FileExistsError("Never overwrite candidate")
    elf,report=apply(a.input.read_bytes())
    a.output.write_bytes(elf)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="patched_inscription_rows"},sort_keys=True))

if __name__=="__main__":main()
