"""Playtest-guided, controller-safe paragraph formatting for 50 r67 Help bodies.

Input is the existing frozen r67 inspection ELF, not the pristine executable.
Only the 50 already-proven r67 Help TABLE DESCRIPTORS are redirected. No
accepted H.A.N.T. geometry/metadata, AFK/L1 code, or save identity is touched.
"""
from __future__ import annotations

from collections import defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.first_save_help import (
    _raw_rows, _metadata, _icon_reservations, _normalized_english,
    _reflow_page, SEMANTIC_CONTROLS, COMPACT_HELP_ROWS, _MAX_CELLS,
)
from tools.first_save_help_inventory import _BLANK, _EOF
from tools.inspect_english_bytes import parse as parse_official
from tools.localization import encode_ps2_english


# The user's in-game screenshots prove that automatically fusing the command
# rows produces unreadable Help on these two icon-heavy pages. Preserve each
# native icon's existing row and user input, but use concise command captions.
# Basic Attack froze after the text-table rewrite in the latest playtest.
# Retain its previously playable r67 table and all sprite descriptors until
# runtime has isolated the exact failure; do not deploy a second guess.
FREEZE_SAFETY_ROLLBACK = frozenset({"basic_attack"})

READABLE_ICON_PAGES: dict[str, tuple[str, ...]] = {
    "turn_based_combat": (
        "Turns", "",
        "Combat alternates by turn.",
        "and the enemy each turn.", "", "",
        "AP .........................", "",
        "Moves and attacks use AP.",
        "Each action reduces your AP.", "",
        "When AP is depleted, you",
        "cannot act until next turn.", "", "", "",
        "Recovering AP .............", "",
        "Your AP returns to maximum",
        "when your turn begins.", "",
        "Some items can restore AP.", "", "",
        "Ending Your Turn ..........", "",
        "Press        to end turn.",
        "Your turn ends.", "",
    ),
    "entering_battle": (
        "     Exploration to Combat", "",
        "Enemies trigger combat mode.", "",
        "     Press to enter combat.", "",
        "Combat Mode Controls", "",
        "      Move", "      Ready weapon / fire", "      Ready weapon / fire",
        "      Ready weapon / fire", "      Change stance",
        "      Select buddy skill", "      End turn", "      Night vision",
        "      Aim with R Stick", "",
    ),
    "basic_attack": (
        "Basic Attack", "",
        "1. Move into position.", "",
        "2. Equip a weapon.", "Press          to equip.", "",
        "",
        "3.     Aim with R Stick.",
        "Aim at the target.", "",
        "", "4. Press the equipped",
        "weapon button to attack.", "",
        "5. Out of AP? End turn.",
        "       Press to end turn.", "",
        "", "     End your turn early",
        "even with AP remaining.", "",
    ),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reflow_readable(
    pristine: bytes, page: dict, english: dict[str, set[str]]
) -> tuple[str, ...]:
    rows = _raw_rows(pristine, page)
    reserved, _ = _icon_reservations(page, _metadata(pristine, page))
    if page["key"] in FREEZE_SAFETY_ROLLBACK:
        return _reflow_page(rows, english, reserved, page["key"])[0]
    if page["key"] in READABLE_ICON_PAGES:
        arranged = READABLE_ICON_PAGES[page["key"]]
    else:
        sections: list[list[str]] = []
        current: list[str] = []
        for row in rows:
            if row is None:
                if current:
                    sections.append(current)
                    current = []
                continue
            source_offset, data = row
            japanese = data[:-1].decode("cp932")
            matches = english.get(japanese, set())
            if source_offset in COMPACT_HELP_ROWS.get(page["key"], {}):
                text = COMPACT_HELP_ROWS[page["key"]][source_offset]
            elif len(matches) == 1:
                text = next(iter(matches))
            elif source_offset in SEMANTIC_CONTROLS:
                text = SEMANTIC_CONTROLS[source_offset]
            else:
                raise ValueError(f"Unmapped official Help source {page['key']}/{source_offset:x}")
            text = _normalized_english(text).strip()
            if text and set(text) <= set("-_"):
                if current:
                    sections.append(current)
                    current = []
            elif text:
                current.append(text)
        if current:
            sections.append(current)

        def attempt(gap: int) -> tuple[str, ...] | None:
            canvas = [""] * page["rows"]
            cursor = 0
            for section_no, section in enumerate(sections):
                if section_no:
                    cursor += gap
                words = " ".join(section).split()
                while words:
                    if cursor >= page["rows"]:
                        return None
                    indent = max(reserved[cursor]) + 1 if reserved[cursor] else 0
                    limit = _MAX_CELLS - indent
                    if limit <= 0:
                        return None
                    taken: list[str] = []
                    while words and len(" ".join(taken + [words[0]])) <= limit:
                        taken.append(words.pop(0))
                    if not taken:
                        cursor += 1
                        continue
                    canvas[cursor] = " " * indent + " ".join(taken)
                    cursor += 1
            return tuple(canvas)

        arranged = attempt(1) or attempt(0)
        if arranged is None:
            raise ValueError(f"Polished Help does not fit owned rows: {page['key']}")

    if len(arranged) != page["rows"]:
        raise ValueError(f"Changed Help row count: {page['key']}")
    for row_no, text in enumerate(arranged):
        if len(text) > _MAX_CELLS:
            raise ValueError(f"Help row overwide: {page['key']}/{row_no}")
        if any(x < len(text) and text[x] != " " for x in reserved[row_no]):
            raise ValueError(f"Overlaps gamepad icon: {page['key']}/{row_no}")
        if len(text) >= 8 and "--------" in text:
            raise ValueError(f"Unremoved decorative separator: {page['key']}/{row_no}")
    return tuple(arranged)


def append_polished_help(
    pristine: bytes, original_help: bytes, base: bytes, manifest: dict,
    english_rows: list[tuple[str, str, int]], expected_base_hash: str
) -> tuple[bytes, dict]:
    if sha(base) != "01918e4c5edd23220dfdedfa33701baa610f6fda3e427024c5e0193d80e6ca11" or sha(base) != expected_base_hash:
        raise ValueError("Input r67 playtest inspection ELF changed")
    if sha(original_help) != "26db69bd46e119ecbb7f114ecdafc678976294460f56b7a214861de82c95d76a":
        raise ValueError("Original translated r67 Help baseline changed")
    if len(manifest["pages"]) != 50 or sha(pristine) != manifest["pristine_elf_sha256"]:
        raise ValueError("Unapproved Help source manifest")
    _typ, fo, va, _pa, length, reserve, flags, _align = struct.unpack_from("<8I", base, 0x54)
    if fo + length != len(base) or va != 0x902F00 or reserve != 0x100000 or flags != 7:
        raise ValueError("Unexpected translation PT_LOAD")
    dictionary: dict[str, set[str]] = defaultdict(set)
    for japanese, english, _ in english_rows:
        dictionary[japanese].add(english)
    out = bytearray(base)
    allowed=set(range(0x64,0x68))
    metadata: list[dict] = []

    def append(content: bytes, alignment: int = 2) -> int:
        while len(out) % alignment:
            out.append(0)
        target = va + len(out) - fo
        out.extend(content)
        return target

    for page in manifest["pages"]:
        # Verify the current text-table descriptor is precisely the existing
        # r67 owner, not an unrelated stale owner with a colliding pointer.
        ptr=page["descriptor_offset"]
        old_va=struct.unpack_from("<I",original_help,ptr)[0]
        if struct.unpack_from("<I",base,ptr)[0]!=old_va:
            raise ValueError(f"Help descriptor altered after original pass: {page['key']}")
        old_off=fo+old_va-va
        if old_off < fo or old_off >= len(original_help):
            raise ValueError(f"Help descriptor not in accepted translation segment: {page['key']}")
        current = _reflow_page(
            _raw_rows(pristine,page),dictionary,
            _icon_reservations(page,_metadata(pristine,page))[0],page["key"]
        )[0]
        for row_no,line in enumerate(current):
            existing_ptr=struct.unpack_from("<I",base,old_off+row_no*4)[0]
            if line:
                location=fo+existing_ptr-va
                encoded=encode_ps2_english(line,collapse_spaces=False)+b"\0"
                if base[location:location+len(encoded)]!=encoded:
                    raise ValueError(f"Prior r67 Help row changed: {page['key']}/{row_no}")
            elif existing_ptr != _BLANK:
                raise ValueError(f"Prior Help blank row changed: {page['key']}/{row_no}")
        if struct.unpack_from("<I",base,old_off+page["rows"]*4)[0]!=_EOF:
            raise ValueError(f"Old Help table EOF changed: {page['key']}")

        if page["key"] in FREEZE_SAFETY_ROLLBACK:
            # A known playable original r67 table. Preserve the exact
            # descriptor and its referenced bytes, not merely equivalent text.
            metadata.append(dict(key=page["key"],rows=page["rows"],
                                 old_table_va=old_va,polished_table_va=old_va,
                                 first_line=current[0],changed_lines=0,
                                 frozen_for_freeze_investigation=True))
            continue
        lines=reflow_readable(pristine,page,dictionary)
        pointers=[
            append(encode_ps2_english(line,collapse_spaces=False)+b"\0") if line else _BLANK
            for line in lines
        ]
        target=append(struct.pack("<"+"I"*(len(pointers)+1),*(pointers+[_EOF])),4)
        struct.pack_into("<I",out,ptr,target)
        allowed.update(range(ptr,ptr+4))
        metadata.append(dict(key=page["key"],rows=len(lines),old_table_va=old_va,
                             polished_table_va=target,first_line=lines[0],
                             changed_lines=sum(a!=b for a,b in zip(lines,current))))
        # The accompanying controller icons stay EXACTLY where the approved
        # r67 pass placed them; no metadata descriptor is changed.
        icon_descriptor=page["metadata_descriptor_offset"]
        if base[icon_descriptor:icon_descriptor+4]!=original_help[icon_descriptor:icon_descriptor+4]:
            raise ValueError(f"Help icon geometry unexpectedly changed: {page['key']}")

    struct.pack_into("<I",out,0x64,len(out)-fo)
    if len(out)-fo>reserve:
        raise ValueError("Translated region RAM exhausted")
    for i,(a,b) in enumerate(zip(base,out)):
        if a!=b and i not in allowed:
            raise ValueError(f"Unowned change to approved r67: {i:#x}")
    return bytes(out),dict(
        schema_version=1,pages=len(metadata),changed_pages=sum(m["changed_lines"]>0 for m in metadata),
        changed_rows=sum(m["changed_lines"] for m in metadata),input_sha256=sha(base),
        output_sha256=sha(out),appended_bytes=len(out)-len(base),
        pages_detail=metadata,
    )


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pristine",type=Path,required=True)
    p.add_argument("--original-help",type=Path,required=True)
    p.add_argument("--baseline",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--official",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():
        raise FileExistsError("Refusing to overwrite candidate")
    manifest=json.loads(a.manifest.read_text())
    if sha(a.official.read_bytes())!=manifest["official_ps4_english_sha256"]:
        raise ValueError("Official English source drift")
    out,report=append_polished_help(
        a.pristine.read_bytes(),a.original_help.read_bytes(),a.baseline.read_bytes(),
        manifest,parse_official(a.official),sha(a.baseline.read_bytes())
    )
    a.output.write_bytes(out)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print({k:v for k,v in report.items() if k!="pages_detail"})


if __name__=="__main__":
    main()
