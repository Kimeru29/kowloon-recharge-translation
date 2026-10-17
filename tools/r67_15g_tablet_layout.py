"""Narrow r67.15g punctuation and centering correction for the western clue."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from tools.inspect_english_bytes import parse as parse_english
from tools.localization import encode_ps2_english
from tools.r67_14q_approved_lock import MANIFEST as Q_MANIFEST, verify_approved
from tools.r67_14t_approved_ui_lock import MANIFEST as T_MANIFEST, verify_ui
from tools.r67_14t_stone_tablet_fit import assert_all_tablets_fit, read_string
from tools.r67_chamber_story_text_only import (
    ELF_SEGMENT_FO,
    ELF_SEGMENT_RESERVE,
    ELF_SEGMENT_VA,
)
from tools.r67_lion_statue_ui import ELF_BIAS, sha

CORPUS = Path("/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes")
CORPUS_SHA256 = "b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b"
SOURCE_SEGMENT_FILE_OFFSET = 0x803150
SOURCE_SEGMENT_VA = 0x902F00
TABLET_RECORD = 0x590FB0
ROW_OWNERS = (0x590FB8, 0x590FBC, 0x590FC0)
SOURCE_POINTERS = (0x9640BA, 0x9640DA, 0x964102)
SOURCE_ROW_SHA256 = (
    "391e695581f596c8b936421faf5ddd40fa661a5927e1a4eaa850b3447d121c60",
    "ac7deb82a09b63436532b53dfa64144a180a44b49879907f8d49c408b108c999",
    "8b6d862663387ef715bd61146e6ef2ab547ab2ba81135cbd3f3556cabba9cd20",
)
TABLET_TITLE_POINTER = 0x962C7A
CENTERING_WIDTH_CELLS = 21
MAX_ELF_SEGMENT_SIZE = ELF_SEGMENT_FO + ELF_SEGMENT_RESERVE

# Half-open original-file offsets. The segment-size field is allowed to grow;
# only the western clue's three pointer words are otherwise owned here.
PERMITTED_EXISTING_RANGES = ((0x64, 0x68), (0x590FB8, 0x590FC4))

# These exact official rows establish the meaning and provenance for the
# historically accepted compact wording retained by this presentation fix.
OFFICIAL_ROWS = (
    (0xCC448, "　”《頭を垂れて》", "　\"The one with a lowered head"),
    (0xCC48A, "　　《西》へと歩くものに", "　　that walks to the west"),
    (0xCC4D2, "　　神の慈悲は舞い降りん。”", "　　will receive the mercy of god.\""),
)
ACCEPTED_TEXT = ("The bowed one", "walks west, finds", "the mercy of God.")


def _validate_header(source: bytes) -> None:
    if not source.startswith(b"\x7fELF"):
        raise ValueError("Source is not a PS2 ELF")
    typ, fo, va, _unused, size, reserve, flags, align = struct.unpack_from("<8I", source, 0x54)
    if (typ, fo, va, fo + size, reserve, flags, align) != (
        1, ELF_SEGMENT_FO, ELF_SEGMENT_VA, len(source), ELF_SEGMENT_RESERVE, 7, 16
    ):
        raise ValueError("ELF translation segment format changed")


def _verify_source_owners(source: bytes) -> None:
    pointers = struct.unpack_from("<6I", source, TABLET_RECORD)
    if pointers[0] != TABLET_TITLE_POINTER or pointers[5] != 0x962C94:
        raise ValueError("Western tablet record title/end-marker preimage changed")
    if pointers[1] != 0x962D3C:
        raise ValueError("Western tablet description owner changed")
    for owner, expected_pointer, expected_sha in zip(
        ROW_OWNERS, SOURCE_POINTERS, SOURCE_ROW_SHA256, strict=True
    ):
        actual_pointer = struct.unpack_from("<I", source, owner)[0]
        if actual_pointer != expected_pointer:
            raise ValueError(f"Western tablet pointer preimage changed at {owner:#x}")
        actual_text = read_string(source, actual_pointer)
        if hashlib.sha256(actual_text).hexdigest() != expected_sha:
            raise ValueError(f"Western tablet string preimage changed at {owner:#x}")


def _verify_official_corpus(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError("Official PS4 English corpus is unavailable")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != CORPUS_SHA256:
        raise ValueError("Official PS4 English corpus hash changed")
    by_offset = {offset: (jp, en) for jp, en, offset in parse_english(path)}
    evidence = []
    for offset, source_jp, source_en in OFFICIAL_ROWS:
        if by_offset.get(offset) != (source_jp, source_en):
            raise ValueError(f"Official western-tablet source mapping changed at {offset:#x}")
        evidence.append({"english_bytes_offset": hex(offset), "japanese": source_jp, "official_english": source_en})
    return evidence


def _centered_rows() -> tuple[str, ...]:
    rows = []
    for text in ACCEPTED_TEXT:
        if len(text) > CENTERING_WIDTH_CELLS:
            raise ValueError("Accepted tablet wording exceeds the native 21-cell row bound")
        left = (CENTERING_WIDTH_CELLS - len(text)) // 2
        rows.append("　" * left + text)
    return tuple(rows)


def _reconstruct_14t_owners_for_lock(candidate: bytes) -> bytes:
    """Restore prior Lion/tablet owner words in memory for unchanged t lock."""
    manifest = json.loads(T_MANIFEST.read_text())
    reconstructed = bytearray(candidate)
    for raw_va, raw_word in manifest["item_label_native_callsites"].items():
        struct.pack_into("<I", reconstructed, int(raw_va, 16) - ELF_BIAS, int(raw_word, 16))
    tablet = manifest["accepted_tablet_records"][hex(TABLET_RECORD)]
    expected_pointers = tuple(int(value, 16) for value in tablet["pointer_words"])
    for index in (2, 3, 4):
        struct.pack_into("<I", reconstructed, TABLET_RECORD + index * 4, expected_pointers[index])
    return bytes(reconstructed)


def apply(source: bytes, official_corpus: Path = CORPUS) -> tuple[bytes, dict]:
    """Apply the isolated western-tablet text-pointer and centering update."""
    _validate_header(source)
    _verify_source_owners(source)
    official_rows = _verify_official_corpus(Path(official_corpus))

    original_size = len(source)
    output = bytearray(source)
    patched = []
    for owner, text in zip(ROW_OWNERS, _centered_rows(), strict=True):
        payload = encode_ps2_english(text, collapse_spaces=False) + b"\0"
        if len(output) & 1:
            output.append(0)
        pointer = SOURCE_SEGMENT_VA + len(output) - SOURCE_SEGMENT_FILE_OFFSET
        output.extend(payload)
        struct.pack_into("<I", output, owner, pointer)
        patched.append({
            "owner_file_offset": hex(owner),
            "new_pointer_va": hex(pointer),
            "text": text,
            "glyph_cells": len(text),
            "left_padding_cells": (CENTERING_WIDTH_CELLS - len(text)) // 2,
            "payload_bytes": len(payload),
        })
    while len(output) & 3:
        output.append(0)
    if len(output) > MAX_ELF_SEGMENT_SIZE:
        raise ValueError("ELF translation segment reserve exceeded")
    struct.pack_into("<I", output, 0x64, len(output) - ELF_SEGMENT_FO)

    existing_changes = {
        offset
        for offset, (before, after) in enumerate(zip(source, output[:original_size], strict=True))
        if before != after
    }
    allowed = {offset for start, end in PERMITTED_EXISTING_RANGES for offset in range(start, end)}
    if not existing_changes or existing_changes - allowed:
        raise ValueError(f"Unclassified original ELF changes: {sorted(existing_changes - allowed)}")
    for owner in ROW_OWNERS:
        if not any(start <= owner and owner + 4 <= end for start, end in PERMITTED_EXISTING_RANGES):
            raise ValueError(f"Tablet row pointer outside declared patch ranges: {owner:#x}")

    result = bytes(output)
    fit = assert_all_tablets_fit(result)
    if fit["registered_tablets"] != 58 or fit["populated_tablet_rows"] != 160:
        raise ValueError("Game-wide tablet class coverage changed")

    # Preserve the immutable historical locks without editing/rebasing either
    # manifest: restore the precise prior pointer/callsite words in RAM only.
    reconstructed = _reconstruct_14t_owners_for_lock(result)
    q_lock = verify_approved(reconstructed, json.loads(Q_MANIFEST.read_text()))
    t_lock = verify_ui(reconstructed, json.loads(T_MANIFEST.read_text()))
    if q_lock["approved_regions"] != 4 or t_lock["accepted_tablet_record_count"] != 3:
        raise ValueError("Prior q/t approval lock coverage changed")

    return result, {
        "revision": "r67.15g",
        "status": "DIAGNOSTIC_STATIC_TABLET_LAYOUT_ONLY",
        "source_elf_sha256_for_traceability": sha(source),
        "candidate_elf_sha256": sha(result),
        "source_elf_size": original_size,
        "candidate_elf_size": len(result),
        "appended_extent": {"start": hex(original_size), "end_exclusive": hex(len(result))},
        "modified_existing_offsets": [hex(value) for value in sorted(existing_changes)],
        "modified_tablet_row_owners": [hex(value) for value in ROW_OWNERS],
        "permitted_existing_ranges": [[hex(start), hex(end)] for start, end in PERMITTED_EXISTING_RANGES],
        "native_centering_width_cells": CENTERING_WIDTH_CELLS,
        "rows": patched,
        "official_corpus_sha256": CORPUS_SHA256,
        "official_source_rows": official_rows,
        "accepted_compact_wording_preserved": True,
        "western_quote_markers_removed": True,
        "all_58_tablets_and_160_rows_fit": fit,
        "q_lock_passed_after_in_memory_reconstruction": True,
        "old_14t_ui_lock_passed_after_in_memory_reconstruction": True,
        "reconstruction_scope": ["14t Lion callsite words", "western tablet row pointer words"],
        "approved_manifests_modified": False,
        "unrelated_tablet_records_modified": 0,
        "runtime_verified": False,
        "gameplay_approved": False,
    }
