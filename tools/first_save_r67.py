"""Append-only, fail-closed first-save English owners over *approved r66* ELF.

The original PS2 executable, r66 resources/AFK/L1 payload, and scenario flags
are untouched.  Only the translation segment file size and the 148 proven
pointer aliases are changed, with English text appended inside its preexisting
1 MiB RAM reservation.  Owned PS4 English.bytes is used to prove each phrase.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from tools.inspect_english_bytes import parse as parse_english
from tools.localization import encode_ps2_english

_SEGMENT_HEADER = 0x54
_SEGMENT_TYPE = 1
_SEGMENT_BASE = 0x00902F00
_ELF_MAIN_LOAD_VADDR = 0x00100000
_ELF_MAIN_FILE_OFFSET = 0x80
_EXPECTED_OWNER_COUNT = 29
_EXPECTED_POINTER_COUNT = 148


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def patch_first_save(
    approved_r66: bytes, manifest: dict[str, Any], english_rows: list[tuple[str, str, int]],
    *, english_corpus_sha256: str,
) -> tuple[bytes, dict[str, Any]]:
    """Return patched ELF and an audit record or raise on any source drift."""

    if manifest.get("schema_version") != 1:
        raise ValueError("Unexpected first-save schema")
    if digest(approved_r66) != manifest["approved_r66_elf_sha256"]:
        raise ValueError("Approved r66 ELF SHA256 mismatch")
    if english_corpus_sha256 != manifest["official_english_bytes_sha256"]:
        raise ValueError("Official PS4 English corpus SHA256 mismatch")
    if approved_r66[:4] != b"\x7fELF":
        raise ValueError("Expected PS2 ELF")
    kind, p_offset, p_va, _physical, p_size, p_reserve, flags, align = (
        struct.unpack_from("<8I", approved_r66, _SEGMENT_HEADER)
    )
    if (
        kind != _SEGMENT_TYPE or p_va != _SEGMENT_BASE
        or flags != 7 or align != 0x10 or p_reserve != 0x100000
        or p_offset + p_size != len(approved_r66)
    ):
        raise ValueError("Unexpected approved r66 translation segment geometry")

    official = {offset: (jp, translated) for jp, translated, offset in english_rows}
    records = manifest.get("owners")
    if not isinstance(records, list) or len(records) != _EXPECTED_OWNER_COUNT:
        raise ValueError("Unapproved first-save owner count")
    result = bytearray(approved_r66)
    previous_length = len(result)
    visited: set[str] = set()
    consumed_pointers: set[int] = set()
    audit: list[dict[str, object]] = []

    for entry in records:
        key = entry["key"]
        if key in visited or not isinstance(key, str):
            raise ValueError(f"Duplicate or invalid owner: {key!r}")
        visited.add(key)
        source_offset = entry["source_offset"]
        if not isinstance(source_offset, int) or not (
            _ELF_MAIN_FILE_OFFSET <= source_offset < p_offset
        ):
            raise ValueError(f"Source outside pristine first PT_LOAD: {key}")
        source_end = approved_r66.find(b"\x00", source_offset, p_offset)
        if source_end < 0:
            raise ValueError(f"Unterminated source: {key}")
        source = approved_r66[source_offset:source_end + 1]
        if digest(source) != entry["source_sha256"]:
            raise ValueError(f"Japanese source SHA256 mismatch: {key}")
        try:
            japanese = source[:-1].decode("cp932")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Invalid Japanese source: {key}") from exc

        official_offset = entry["official_record_offset"]
        if official_offset not in official:
            raise ValueError(f"Missing official English record: {key}")
        original_jp, english = official[official_offset]
        if japanese != original_jp or english != entry["official_english"]:
            raise ValueError(f"Official PS4 source correspondence drift: {key}")
        encoded = encode_ps2_english(english) + b"\x00"
        if len(result) & 1:
            result.append(0)
        localized_va = p_va + len(result) - p_offset
        if localized_va & 1:
            raise ValueError(f"Misaligned translation pointer: {key}")
        result.extend(encoded)

        source_va = _ELF_MAIN_LOAD_VADDR + source_offset - _ELF_MAIN_FILE_OFFSET
        source_pointer = struct.pack("<I", source_va)
        literal_owners = {
            index for index in range(0, p_offset - 4, 4)
            if approved_r66[index:index + 4] == source_pointer
        }
        wanted = entry["owner_offsets"]
        if not isinstance(wanted, list) or not wanted:
            raise ValueError(f"Missing approved pointer owners: {key}")
        if set(wanted) != literal_owners or len(wanted) != len(literal_owners):
            raise ValueError(f"Pointer alias set drift: {key}")
        for pointer in wanted:
            if pointer in consumed_pointers:
                raise ValueError(f"Duplicate pointer owner: {pointer:#x}")
            consumed_pointers.add(pointer)
            if not isinstance(pointer, int) or pointer & 3:
                raise ValueError(f"Unaligned owner: {pointer!r}")
            if approved_r66[pointer:pointer + 4] != source_pointer:
                raise ValueError(f"Pointer source preimage drift: {key}")
            struct.pack_into("<I", result, pointer, localized_va)
        audit.append(dict(
            key=key, source_offset=source_offset, owner_offsets=wanted,
            official_record_offset=official_offset, translated_va=localized_va,
            output_size=len(encoded), output_sha256=digest(encoded),
        ))

    if len(consumed_pointers) != _EXPECTED_POINTER_COUNT:
        raise ValueError("First-save pointer count drift")
    new_size = len(result) - p_offset
    if new_size > p_reserve:
        raise ValueError("Translation payload exceeds approved 1 MiB reservation")
    struct.pack_into("<I", result, _SEGMENT_HEADER + 16, new_size)

    # Enforce exact changed-byte classification; ignore the newly appended
    # range but forbid *any* alteration to pre-existing AFK/L1 code/data.
    allowed = {
        *range(_SEGMENT_HEADER + 16, _SEGMENT_HEADER + 20),
        *(b for ptr in consumed_pointers for b in range(ptr, ptr + 4)),
    }
    for offset, (before, after) in enumerate(zip(approved_r66, result)):
        if before != after and offset not in allowed:
            raise ValueError(f"Unclassified approved r66 ELF byte change: {offset:#x}")
    if len(result) <= previous_length:
        raise ValueError("No first-save English payload appended")

    record = dict(
        schema_version=1, approved_r66_sha256=digest(approved_r66),
        new_elf_sha256=digest(result), owner_count=len(audit),
        pointer_count=len(consumed_pointers), append_offset=previous_length,
        appended_bytes=len(result) - previous_length,
        translation_segment_size_before=p_size, translation_segment_size_after=new_size,
        translation_segment_memory_reserved=p_reserve, owners=audit,
    )
    return bytes(result), record


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("approved_r66_elf", type=Path)
    p.add_argument("--approved-manifest", type=Path, required=True)
    p.add_argument("--official-english-bytes", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("Refusing to overwrite an existing candidate/report")
    manifest = json.loads(args.approved_manifest.read_text(encoding="utf-8"))
    english = args.official_english_bytes.read_bytes()
    translated, report = patch_first_save(
        args.approved_r66_elf.read_bytes(), manifest,
        parse_english(args.official_english_bytes),
        english_corpus_sha256=digest(english),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(translated)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "owners"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
