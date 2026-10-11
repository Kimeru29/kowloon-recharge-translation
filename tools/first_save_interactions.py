"""Append exact and semantic first-dungeon inspection labels to the frozen Help ELF.

Only nine reviewed CP932 original source owners are in scope; this is not
a wholesale translation of the engine's global location/object catalog.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.inspect_english_bytes import parse as parse_english
from tools.localization import encode_ps2_english


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def append_first_dungeon_inspections(
    original: bytes, help_elf: bytes, manifest: dict,
    english_rows: list[tuple[str, str, int]], english_sha256: str
) -> tuple[bytes, dict]:
    if manifest.get("schema_version") != 1 or len(manifest.get("owners", ())) != 9:
        raise ValueError("Unexpected first-dungeon optional label manifest")
    if digest(original) != manifest["source_elf_sha256"]:
        raise ValueError("Pristine PS2 ELF SHA mismatch")
    if digest(help_elf) != manifest["help_elf_sha256"]:
        raise ValueError("Frozen Help-inclusive ELF SHA mismatch")
    if english_sha256 != manifest["english_corpus_sha256"]:
        raise ValueError("Official PS4 English SHA mismatch")

    typ, file_offset, va, _pa, length, memsize, flags, align = struct.unpack_from(
        "<8I", help_elf, 0x54
    )
    if (typ, va, memsize, flags, align) != (1, 0x902F00, 0x100000, 7, 16):
        raise ValueError("Unexpected frozen translated ELF program header")
    if file_offset + length != len(help_elf):
        raise ValueError("Frozen Help ELF does not end on translation PT_LOAD")

    entries = {o: (jp, en) for jp, en, o in english_rows}
    translated = bytearray(help_elf)
    approved_aliases: set[int] = set()
    record = []
    for owner in manifest["owners"]:
        key = owner["key"]
        position = owner["source_offset"]
        if not 0x80 <= position < file_offset:
            raise ValueError(f"Source owner outside pristine ELF: {key}")
        end = original.find(b"\x00", position, file_offset)
        if end < 0:
            raise ValueError(f"Unterminated source owner: {key}")
        source = original[position:end+1]
        if digest(source) != owner["source_sha256"]:
            raise ValueError(f"Source owner SHA mismatch: {key}")
        jp = source[:-1].decode("cp932")
        remaster_record = owner["official_record_offset"]
        if owner["provenance"] == "official_exact":
            if remaster_record not in entries or entries[remaster_record] != (jp, owner["english"]):
                raise ValueError(f"Official remaster value drift: {key}")
        elif owner["provenance"] == "semantic_verified_identifier":
            if remaster_record is not None or not owner["english"]:
                raise ValueError(f"Invalid semantic owner: {key}")
        else:
            raise ValueError(f"Unapproved provenance: {key}")

        if len(translated) & 1:
            translated.append(0)
        target = va + len(translated) - file_offset
        encoded = encode_ps2_english(owner["english"]) + b"\x00"
        translated.extend(encoded)
        from_va = 0x100000 + position - 0x80
        expected = struct.pack("<I", from_va)
        actual_owners = {
            ptr for ptr in range(0, file_offset - 4, 4)
            if original[ptr:ptr+4] == expected
        }
        approved = set(owner["approved_pointer_offsets"])
        if not actual_owners or actual_owners != approved:
            raise ValueError(f"Source alias drift: {key}")
        for ptr in owner["approved_pointer_offsets"]:
            if ptr in approved_aliases or help_elf[ptr:ptr+4] != expected:
                raise ValueError(f"Overlapping/modified inspection pointer: {key}/{ptr:#x}")
            approved_aliases.add(ptr)
            struct.pack_into("<I", translated, ptr, target)
        record.append(dict(key=key, target_va=target, pointer_offsets=owner["approved_pointer_offsets"],
                           source_offset=position, english_bytes=len(encoded),
                           provenance=owner["provenance"]))
    if len(approved_aliases) != 78:
        raise ValueError("Unexpected translated inspection pointer count")
    new_size = len(translated) - file_offset
    if new_size > memsize:
        raise ValueError("Translation segment RAM exhausted")
    struct.pack_into("<I", translated, 0x54+16, new_size)
    allow = {*range(0x54+16, 0x54+20),
             *(i for ptr in approved_aliases for i in range(ptr,ptr+4))}
    for i, (a,b) in enumerate(zip(help_elf, translated)):
        if a!=b and i not in allow:
            raise ValueError(f"Unexplained frozen Help change at {i:#x}")
    return bytes(translated), dict(
        schema_version=1, source_help_sha256=digest(help_elf),
        resulting_elf_sha256=digest(translated), aliases=len(approved_aliases),
        appended_bytes=len(translated)-len(help_elf), owners=record,
    )


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("original_elf",type=Path)
    ap.add_argument("help_elf",type=Path)
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--official-english-bytes",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    args=ap.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("Refusing to overwrite saved candidate")
    source=args.official_english_bytes.read_bytes()
    translated, report=append_first_dungeon_inspections(
        args.original_elf.read_bytes(), args.help_elf.read_bytes(),
        json.loads(args.manifest.read_text()), parse_english(args.official_english_bytes),
        digest(source),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(translated)
    args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="owners"},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
