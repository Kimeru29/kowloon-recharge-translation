"""Fail-closed r67 playtest corrections for independent inspection and fixed pickup text.

No user-approved AFK/L1/ADV code paths are touched. Official source text is
loaded from user-owned PS4 English.bytes; compact UI exceptions keep meaning
within observed PS2 renderer constraints. All original pointer aliases are pinned.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.inspect_english_bytes import parse as parse_official
from tools.localization import encode_ps2_english


# Small semantic reflows of individually proven official PS4 English, rather
# than pushing long remaster wording through PS2's narrower inspection panel.
COMPACT_BY_SOURCE_OFFSET = {
    0x590BC0: " Stores valuables.",
    0x590C60: " Cannot be opened yet.",
    0x590D80: " Holds precious items.",
    0x590E80: " Machinery detected inside.",
}

# Two prior r67 literals had been sourced exactly, but rendered far past the
# green chamber inspection panel. Both short rows preserve puzzle instructions.
COMPACT_EARLIER_OWNER = {
    "object_ancient_writing_description": " Ancient Egyptian writing.",
    "lion_inscription_1": "4 fierce beasts face each",
    "lion_inscription_2": "other; the east door opens.",
}

# In PS2 the new-item popup uses independent fixed 24-byte string slots,
# NOT the relocated object inspection owner translated in r67.
COMPACT_PICKUP_ROWS = ("Stone lion", "  statue.")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def append_inspection_fixes(
    pristine: bytes, baseline: bytes, manifest: dict,
    prior_manifest: dict, official_rows: list[tuple[str, str, int]], corpus_hash: str
) -> tuple[bytes, dict]:
    if manifest["schema_version"] != 1 or len(manifest["owners"]) != 14:
        raise ValueError("Unrecognized playtest owner set")
    if sha(pristine) != manifest["pristine_sha256"]:
        raise ValueError("Pristine executable changed")
    if sha(baseline) != manifest["base_r67_elf_sha256"]:
        raise ValueError("Approved r67 baseline mismatch")
    if corpus_hash != manifest["official_english_sha256"]:
        raise ValueError("PS4 English corpus changed")
    _type, fo, va, _pa, size, reserve, _flags, _alignment = struct.unpack_from("<8I", baseline, 0x54)
    if fo + size != len(baseline) or va != 0x902F00 or reserve != 0x100000:
        raise ValueError("Unexpected appended translation segment")

    official = {(jp, offset): en for jp, en, offset in official_rows}
    result = bytearray(baseline)
    allowed: set[int] = set(range(0x64, 0x68))
    pointer_owners: set[int] = set()
    metadata: list[dict] = []

    def append(text: str) -> int:
        if len(result) & 1:
            result.append(0)
        location = va + len(result) - fo
        encoded = encode_ps2_english(text) + b"\0"
        result.extend(encoded)
        return location

    def patch_owner(name: str, pointers: list[int], expected: int, localized: str) -> None:
        if len(localized.strip()) > 34:
            raise ValueError(f"Overwide inspection string {name}: {localized!r}")
        if not pointers:
            raise ValueError(f"No pointer owners: {name}")
        for off in pointers:
            if off in pointer_owners or struct.unpack_from("<I", baseline, off)[0] != expected:
                raise ValueError(f"Unowned or already patched source: {name} {off:#x}")
            pointer_owners.add(off)
            allowed.update(range(off, off + 4))
        dest = append(localized)
        for off in pointers:
            struct.pack_into("<I", result, off, dest)
        metadata.append(dict(key=name, aliases=pointers, target_va=dest, english_bytes=len(encode_ps2_english(localized))))

    for owner in manifest["owners"]:
        offset = owner["offset"]
        end = pristine.find(b"\0", offset, offset + 150)
        source = pristine[offset:end+1]
        if sha(source) != owner["source_sha256"]:
            raise ValueError(f"Text owner fingerprint drift: {offset:#x}")
        japanese = source[:-1].decode("cp932")
        index = owner["ps4_record"]
        if (japanese, index) not in official:
            raise ValueError(f"Unproven official PS4 match: {offset:#x}")
        actual = struct.pack("<I", 0x100000 + offset - 0x80)
        aliases = [i for i in range(0, fo - 4, 4) if pristine[i:i+4] == actual]
        if aliases != owner["aliases"]:
            raise ValueError(f"Pointer ownership drift: {offset:#x}")
        original = struct.unpack("<I", actual)[0]
        text = COMPACT_BY_SOURCE_OFFSET.get(offset, official[(japanese, index)])
        # The official remaster explicitly DELETES the Lion Statue phonetic
        # subtitle; omit that duplicate JP subtitle while keeping its native
        # pointer live, rather than adding a second copy of the main name.
        if offset == 0x5958C8 and text == "@D":
            text = ""
        elif text == "@D":
            raise ValueError(f"Unreviewed PS4-deleted value: {offset:#x}")
        patch_owner(f"native_{offset:x}", aliases, original, text)

    early = {x["key"]: x for x in prior_manifest["owners"]}
    for key, text in COMPACT_EARLIER_OWNER.items():
        owner = early[key]
        original_source = owner["source_offset"]
        jp_end = pristine.find(b"\0", original_source, original_source + 180)
        japanese = pristine[original_source:jp_end].decode("cp932")
        expected_record = owner["official_record_offset"]
        if (japanese, expected_record) not in official:
            raise ValueError(f"Previously official text changed: {key}")
        pointers = owner["owner_offsets"]
        old_destinations = {struct.unpack_from("<I", baseline, x)[0] for x in pointers}
        if len(old_destinations) != 1:
            raise ValueError(f"Current r67 owner aliases disagree: {key}")
        old_va = old_destinations.pop()
        old_off = fo + old_va - va
        expected_bytes = encode_ps2_english(owner["official_english"]) + b"\0"
        if baseline[old_off:old_off+len(expected_bytes)] != expected_bytes:
            raise ValueError(f"Cannot validate prior English string: {key}")
        patch_owner(key, pointers, old_va, text)

    item_offsets = [0x596010, 0x596028]
    for rec, expected_offset, content in zip(
        manifest["fixed_item_pickup_rows"], item_offsets, COMPACT_PICKUP_ROWS, strict=True
    ):
        if rec["offset"] != expected_offset or rec["slot_len"] != 24:
            raise ValueError("Unrecognized fixed item pickup layout")
        off = rec["offset"]
        src_slice = pristine[off:off+24]
        if sha(src_slice) != rec["slot_sha256"] or baseline[off:off+24] != src_slice:
            raise ValueError(f"Fixed item record not pristine: {off:#x}")
        encoded = encode_ps2_english(content) + b"\0"
        if len(encoded) > 24:
            raise ValueError(f"Pickup item row overflows fixed record: {content}")
        result[off:off+24] = encoded.ljust(24, b"\0")
        allowed.update(range(off, off+24))
    struct.pack_into("<I", result, 0x64, len(result) - fo)
    if len(result) - fo > reserve:
        raise ValueError("Translation PT_LOAD exhausted")
    for offset, (a, b) in enumerate(zip(baseline, result)):
        if a != b and offset not in allowed:
            raise ValueError(f"Unexpected r67 executable modification at {offset:#x}")
    return bytes(result), dict(
        updated_origins=len(metadata), changed_pointer_owners=len(pointer_owners),
        fixed_item_rows=len(COMPACT_PICKUP_ROWS), original_elf_sha256=sha(baseline),
        result_elf_sha256=sha(result), original_size=len(baseline), result_size=len(result),
        text_owners=metadata,
    )


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pristine",type=Path,required=True)
    p.add_argument("--baseline",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--previous-manifest",type=Path,required=True)
    p.add_argument("--official",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():
        raise FileExistsError("Refusing to overwrite runtime candidate")
    corpus=a.official.read_bytes()
    output,report=append_inspection_fixes(
        a.pristine.read_bytes(),a.baseline.read_bytes(),
        json.loads(a.manifest.read_text()),json.loads(a.previous_manifest.read_text()),
        parse_official(a.official),sha(corpus)
    )
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_bytes(output)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print({k:v for k,v in report.items() if k!="text_owners"})


if __name__ == "__main__":
    main()
