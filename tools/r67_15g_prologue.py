"""Append exact prologue labels and safely pack the optional Anubis Enemy rows."""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from tools.inspect_english_bytes import parse as parse_english
from tools.hant_layout import HANT_LAYOUT_PROFILE, measured_hant_cells, wrap_hant_text
from tools.localization import encode_ps2_english
from tools.r67_chamber_story_text_only import (
    ELF_SEGMENT_FO,
    ELF_SEGMENT_RESERVE,
    ELF_SEGMENT_VA,
)


ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path("/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes")
CORPUS_SHA256 = "b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b"
BASE_15F_SHA256 = "418864fdb8700f100218a1dcb06aa90d71ce45b8ca5b98aaa9a8d46171378da1"
BASE_15F_ELF = ROOT / "local/r67-15f-item-panel-layout.elf"
ELF_MAIN_FILE_OFFSET = 0x80
ELF_MAIN_LOAD_VADDR = 0x00100000
ELF_SEGMENT_HEADER = 0x54
MAX_ELF_SEGMENT_SIZE = ELF_SEGMENT_FO + ELF_SEGMENT_RESERVE

# Each owner has a unique CP932 source, literal 32-bit pointer owner, and
# official PS4 record offset. Corpus prose itself is loaded at build time.
TRANSLATED_OWNERS = (
    {
        "key": "altar_room_name",
        "source_offset": 0x5CCDC0,
        "source": "アヌビスの祭壇（アヌビスのさいだん）",
        "source_sha256": "0ff60422d1570a1b7b2bfd828cd9475e57c2dafa898d2abf59417a8663b08860",
        "pointer_offsets": (0x5CD794,),
        "official_record_offset": 0xC3CB8,
    },
    {
        "key": "anubis_boss_name",
        "source_offset": 0x594B08,
        "source": "アヌビス",
        "source_sha256": "4166f08fc5653443f6520f53f5f8517c6eb5178947fbe0b12a0741b5a7e299f5",
        "pointer_offsets": (0x594E78,),
        "official_record_offset": 0x660B3,
    },
)

# This is the complete nonblank text inventory of the Anubis record in the
# distinct mode-2 H.A.N.T. Enemy hierarchy. Several heading/value strings are
# shared with other enemies; the record-field slots, not every global alias,
# identify the Anubis-only owners. Keep all fields immutable until the selected
# page's row geometry/capacity is proven.
HANT_ANUBIS_ROWS = (
    (0x5BE178, 0x5C2410, "【化人名】", 0xA9E2E, "19169c9b5876224e7a1d5a7b41be0c9bf597bcc5c42331b16806069b7b9b374b"),
    (0x5C2328, 0x5C2414, "　アヌビス", 0xACC8B, "814fe5573667415ffc3a912ccc569fc4dc13812499d3ccec84942c81e5f9eeae"),
    (0x5BE1A8, 0x5C2418, "【分類】", 0xA9E89, "5c557ccb53ca556b86b8371c59d733b95f5b03e79196525dedcbc4b483c25e50"),
    (0x5BE730, 0x5C241C, "　死人（しびと）", 0xACCAB, "0252d631b5a4c20d2660e4c2eb5eb3b5e2b1245d6ed35854383821842ad750b6"),
    (0x5BE1E0, 0x5C2420, "【ＨＰ／弱点ＨＰ】", 0xA9ECD, "5afe18b0a7c5ce9fec6ca7cbdf93e4de3fef000ba26d9b06ad0ea4e3dcce6bef"),
    (0x5BE1F8, 0x5C2428, "【急所】", 0xA9F00, "4a158741f8136b3513872fa8f4328d8bc2207c9e259c4cadb5bc2adb15178f3f"),
    (0x698760, 0x5C242C, "　眉間", 0xAA55E, "d92f41cfc58f6b62ae32f5ffd561401c60c04e45d8e30638de4c7f742e0c8a5a"),
    (0x5BE208, 0x5C2430, "【攻撃方法】", 0xA9F37, "fe886678fced41571a2ee8634f0199e7433647ea4f580bf08907e87fbb247930"),
    (0x5C2340, 0x5C2434, "　【射撃】口から腫瘍を吐く。", 0xACCD4, "a72456a52ab1dee7b01b71fe9f06c6f752b43981cc6df234ab2ff87943a315c0"),
    (0x5BE248, 0x5C2438, "【解説】", 0xA9FBC, "c9cd69eab955e012cda13f43945ca65d3affecf38dab67deabb547d03cbcfad7"),
    (0x5C2360, 0x5C243C, "　死を告げる冥府の王。", 0xACD21, "70d7fe3c92f84d936ba2266d18c56d849bd6d0df92e248bf8ff60606303efb47"),
    (0x5C2380, 0x5C2440, "　犬またはジャッカルの姿で表され、墓所に", 0xACD71, "670a216376945ec4badecbac68936959a7f7b5ddcde9a47bf42194b3ee44aec3"),
    (0x5C23B0, 0x5C2444, "　侵入した盗掘者たちは、アヌビスが描かれ", 0xACDDA, "dacba4b705d0058e2ab397ff81e71fd69dd2e0dbcf5b3ea4f37f24e119fcae17"),
    (0x5C23E0, 0x5C2448, "　た壁画や彫刻を見る事ができる。", 0xACE48, "6c75a4a28ef4eaf4d3789529d91cf5a773125cba2dacc760c9b35d01a60a91c8"),
    (0x5BE318, 0x5C244C, "【特記事項】", 0xAA180, "ce12ca4d9bb26c36b40a92cd5fecb0d739ddec53b48b84dd82ec16d3f81e3809"),
    (0x5BE840, 0x5C2450, "　【火炎】【破邪】に弱い。", 0xACE8D, "22eda2871e9930a77aaba5b08dc68908c85e551a7e79c1be2401d53cfab5e6dd"),
    (0x5BE358, 0x5C2454, "【宝物】", 0xAA204, "161476d41fe3868040844f2efd809790fff777cd4ae356d31e6d22d6b1553108"),
)
HANT_ANUBIS_POINTERS = tuple(pointer for _source, pointer, _jp, _record, _sha in HANT_ANUBIS_ROWS)
HANT_MODE_ROOT_FILE_OFFSET = 0x5CBB40
HANT_ENEMY_MODE = 2
HANT_ENEMY_CATEGORY = 1
HANT_ANUBIS_INDEX = 0
HANT_ENEMY_CATEGORY_TABLE_FILE_OFFSET = 0x5C2A30
HANT_ANUBIS_ENEMY_INDEX_TABLE_FILE_OFFSET = 0x5C29B0
HANT_ANUBIS_RECORD_TABLE_FILE_OFFSET = 0x5C2410
HANT_ANUBIS_RECORD_EOF_FILE_OFFSET = 0x5C2460
HANT_ANUBIS_BLANK_FIELDS = (0x5C2424, 0x5C2458, 0x5C245C)
HANT_ANUBIS_DYNAMIC_ROW_INDICES = (5, 7, 18)
HANT_ANUBIS_PACKED_ROW_INDICES = tuple(range(10, 18))
HANT_ANUBIS_CONSTRUCTOR_EXTENT_PIXELS = 512
HANT_ANUBIS_KNOWN_CONSERVATIVE_TEXT_WIDTH_PIXELS = 336
HANT_ANUBIS_KNOWN_CONSERVATIVE_MAX_CELLS = 28
HANT_ANUBIS_ROW_X_PIXELS = 85
HANT_ANUBIS_ROW_Y_PIXELS = 131
HANT_ANUBIS_ROW_SPACING_PIXELS = 21
HANT_ANUBIS_MAX_DISPLAY_ROWS = 16
HANT_ANUBIS_ROW_BUFFER_BYTES = 0x40

# Half-open original-file offsets. Segment p_filesz is separately declared
# because every append-only component owns that single ELF metadata word.
PERMITTED_EXISTING_RANGES = (
    (0x594E78, 0x594E7C),
    (0x5C2410, 0x5C2424),
    (0x5C2428, 0x5C2458),
    (0x5CD794, 0x5CD798),
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_header(source: bytes) -> None:
    if not source.startswith(b"\x7fELF"):
        raise ValueError("Source is not a PS2 ELF")
    typ, file_offset, va, _physical, size, reserve, flags, align = struct.unpack_from(
        "<8I", source, ELF_SEGMENT_HEADER
    )
    if (typ, file_offset, va, file_offset + size, reserve, flags, align) != (
        1,
        ELF_SEGMENT_FO,
        ELF_SEGMENT_VA,
        len(source),
        ELF_SEGMENT_RESERVE,
        7,
        16,
    ):
        raise ValueError("ELF translation segment format changed")


def _main_va(source_offset: int) -> int:
    return ELF_MAIN_LOAD_VADDR + source_offset - ELF_MAIN_FILE_OFFSET


def _literal_pointer_owners(source: bytes, source_offset: int) -> tuple[int, ...]:
    pointer = struct.pack("<I", _main_va(source_offset))
    return tuple(
        offset
        for offset in range(ELF_MAIN_FILE_OFFSET, ELF_SEGMENT_FO - 3, 4)
        if source[offset : offset + 4] == pointer
    )


def _source_bytes(source: bytes, offset: int, expected_text: str, expected_sha256: str) -> bytes:
    end = source.find(b"\0", offset, ELF_SEGMENT_FO)
    if end < 0:
        raise ValueError(f"Unterminated source preimage at {offset:#x}")
    raw = source[offset : end + 1]
    if raw[:-1].decode("cp932") != expected_text or _sha(raw) != expected_sha256:
        raise ValueError(f"Source text preimage changed at {offset:#x}")
    return raw


def _load_official(corpus_path: Path) -> tuple[dict[int, tuple[str, str]], str]:
    if not corpus_path.is_file():
        raise ValueError("Official PS4 English corpus is unavailable")
    corpus_bytes = corpus_path.read_bytes()
    corpus_sha = _sha(corpus_bytes)
    if corpus_sha != CORPUS_SHA256:
        raise ValueError("Official PS4 English corpus hash changed")
    indexed = {offset: (japanese, english) for japanese, english, offset in parse_english(corpus_path)}
    return indexed, corpus_sha


def _validate_official_row(
    indexed: dict[int, tuple[str, str]], offset: int, japanese: str, *, owner: str
) -> str:
    record = indexed.get(offset)
    if record is None or record[0] != japanese:
        raise ValueError(f"Official corpus source mapping changed for {owner} at {offset:#x}")
    try:
        encode_ps2_english(record[1])
    except ValueError as exc:
        raise ValueError(f"Official text is not representable in the PS2 English font: {owner}") from exc
    return record[1]


def _verify_translated_owners(source: bytes, indexed: dict[int, tuple[str, str]]) -> list[dict]:
    rows = []
    for owner in TRANSLATED_OWNERS:
        position = owner["source_offset"]
        _source_bytes(source, position, owner["source"], owner["source_sha256"])
        actual_aliases = _literal_pointer_owners(source, position)
        if actual_aliases != owner["pointer_offsets"]:
            raise ValueError(f"Pointer owner preimage/alias set changed for {owner['key']}")
        expected_pointer = struct.pack("<I", _main_va(position))
        for pointer_offset in owner["pointer_offsets"]:
            if source[pointer_offset : pointer_offset + 4] != expected_pointer:
                raise ValueError(f"Pointer preimage changed for {owner['key']} at {pointer_offset:#x}")
        english = _validate_official_row(
            indexed, owner["official_record_offset"], owner["source"], owner=owner["key"]
        )
        rows.append({**owner, "english": english})
    return rows


def _inventory_optional_hant_page(
    source: bytes, indexed: dict[int, tuple[str, str]]
) -> list[dict]:
    root_va = struct.unpack_from("<I", source, HANT_MODE_ROOT_FILE_OFFSET + HANT_ENEMY_MODE * 4)[0]
    if root_va != _main_va(HANT_ENEMY_CATEGORY_TABLE_FILE_OFFSET):
        raise ValueError("H.A.N.T. Enemy mode-table preimage changed")
    category_va = struct.unpack_from(
        "<I", source, HANT_ENEMY_CATEGORY_TABLE_FILE_OFFSET + HANT_ENEMY_CATEGORY * 4
    )[0]
    if category_va != _main_va(HANT_ANUBIS_ENEMY_INDEX_TABLE_FILE_OFFSET):
        raise ValueError("H.A.N.T. Enemy category-table preimage changed")
    record_va = struct.unpack_from(
        "<I", source, HANT_ANUBIS_ENEMY_INDEX_TABLE_FILE_OFFSET + HANT_ANUBIS_INDEX * 4
    )[0]
    if record_va != _main_va(HANT_ANUBIS_RECORD_TABLE_FILE_OFFSET):
        raise ValueError("Anubis Enemy record-table preimage changed")
    if struct.unpack_from("<I", source, HANT_ANUBIS_RECORD_EOF_FILE_OFFSET)[0] != 0x795FBC:
        raise ValueError("Anubis Enemy record terminator changed")
    for blank_offset in HANT_ANUBIS_BLANK_FIELDS:
        if struct.unpack_from("<I", source, blank_offset)[0] != 0x795FB8:
            raise ValueError(f"Anubis Enemy blank field changed at {blank_offset:#x}")

    rows = []
    for source_offset, pointer_offset, japanese, official_offset, expected_sha256 in HANT_ANUBIS_ROWS:
        _source_bytes(
            source,
            source_offset,
            japanese,
            expected_sha256,
        )
        expected_pointer = struct.pack("<I", _main_va(source_offset))
        if source[pointer_offset : pointer_offset + 4] != expected_pointer:
            raise ValueError(f"Optional H.A.N.T. source pointer changed at {pointer_offset:#x}")
        english = _validate_official_row(indexed, official_offset, japanese, owner="optional Anubis Enemy page")
        rows.append({
            "source_offset": hex(source_offset),
            "record_field_offset": hex(pointer_offset),
            "source_row_index": (pointer_offset - HANT_ANUBIS_RECORD_TABLE_FILE_OFFSET) // 4,
            "official_record_offset": hex(official_offset),
            "japanese": japanese,
            "source_sha256": expected_sha256,
            "official_english": english,
            "translated": True,
        })
    return rows


def _pack_anubis_description_rows(rows: list[dict]) -> tuple[str, tuple[str, ...]]:
    selected = [row for row in rows if row["source_row_index"] in HANT_ANUBIS_PACKED_ROW_INDICES]
    if tuple(row["source_row_index"] for row in selected) != HANT_ANUBIS_PACKED_ROW_INDICES:
        raise ValueError("Anubis description source-row owner set changed")
    word_stream = " ".join(row["official_english"].lstrip("　 ") for row in selected)
    wrapped = wrap_hant_text(word_stream, HANT_ANUBIS_KNOWN_CONSERVATIVE_MAX_CELLS)
    if len(wrapped) != len(HANT_ANUBIS_PACKED_ROW_INDICES):
        raise ValueError("Anubis description no longer fits the eight fixed native row slots")
    if any(measured_hant_cells(line) > HANT_ANUBIS_KNOWN_CONSERVATIVE_MAX_CELLS for line in wrapped):
        raise ValueError("Wrapped Anubis description exceeds the conservative 336-pixel span")
    if any(len(encode_ps2_english(line)) + 1 > HANT_ANUBIS_ROW_BUFFER_BYTES for line in wrapped):
        raise ValueError("Wrapped Anubis description exceeds the native 0x40-byte copy capacity")
    return word_stream, wrapped


def _describe_anubis_page_constraints(rows: list[dict]) -> dict:
    encoded_rows = [encode_ps2_english(row["official_english"]) for row in rows]
    cell_widths = [measured_hant_cells(row["official_english"]) for row in rows]
    if not rows:
        raise ValueError("Anubis Enemy page has no official rows to inventory")
    return {
        "font_style": 1,
        "glyph_advance_pixels": HANT_LAYOUT_PROFILE.glyph_advance,
        "row_x_pixels": HANT_ANUBIS_ROW_X_PIXELS,
        "row_y_pixels": HANT_ANUBIS_ROW_Y_PIXELS,
        "row_spacing_pixels": HANT_ANUBIS_ROW_SPACING_PIXELS,
        "constructor_extent_pixels": HANT_ANUBIS_CONSTRUCTOR_EXTENT_PIXELS,
        "proven_usable_text_width_pixels": None,
        "known_conservative_text_width_pixels": HANT_ANUBIS_KNOWN_CONSERVATIVE_TEXT_WIDTH_PIXELS,
        "known_conservative_max_cells": HANT_ANUBIS_KNOWN_CONSERVATIVE_MAX_CELLS,
        "conservative_width_bound_applied": True,
        "max_official_glyph_cells": max(cell_widths),
        "max_official_row_pixels": max(cell_widths) * HANT_LAYOUT_PROFILE.glyph_advance,
        "max_exact_encoded_row_bytes": max(map(len, encoded_rows)),
        "max_display_rows": HANT_ANUBIS_MAX_DISPLAY_ROWS,
        "row_buffer_bytes": HANT_ANUBIS_ROW_BUFFER_BYTES,
        "max_row_bytes_including_nul": max(map(len, encoded_rows)) + 1,
        "row_copy_capacity_bytes": HANT_ANUBIS_ROW_BUFFER_BYTES,
        "exact_rows_exceed_native_copy_capacity": max(map(len, encoded_rows)) + 1 > HANT_ANUBIS_ROW_BUFFER_BYTES,
        "reflowed": True,
        "source_row_indices_preserved": True,
    }


def apply(source: bytes, official_corpus: Path = CORPUS) -> tuple[bytes, dict]:
    """Append the proven Altar and Anubis labels over an approved 15f ELF.

    Existing append-only payloads are accepted. The component pins its own
    source strings and pointer words against the 15f preimages, not the whole
    ELF hash, so sequential integration remains deterministic.
    """
    _validate_header(source)
    indexed, corpus_sha = _load_official(Path(official_corpus))
    rows = _verify_translated_owners(source, indexed)
    optional_rows = _inventory_optional_hant_page(source, indexed)
    hant_constraints = _describe_anubis_page_constraints(optional_rows)
    packed_word_stream, packed_lines = _pack_anubis_description_rows(optional_rows)
    packed_by_index = dict(zip(HANT_ANUBIS_PACKED_ROW_INDICES, packed_lines, strict=True))
    hant_translation_rows = []
    for row in optional_rows:
        source_index = row["source_row_index"]
        rendered_english = packed_by_index.get(source_index, row["official_english"])
        row["rendered_english"] = rendered_english
        row["translated"] = True
        hant_translation_rows.append({
            "key": f"hant_anubis_field_{source_index}",
            "source_offset": int(row["source_offset"], 16),
            "pointer_offsets": (int(row["record_field_offset"], 16),),
            "official_record_offset": int(row["official_record_offset"], 16),
            "english": rendered_english,
        })
    rendered_widths = [measured_hant_cells(row["english"]) for row in hant_translation_rows]
    rendered_byte_lengths = [len(encode_ps2_english(row["english"])) + 1 for row in hant_translation_rows]
    if max(rendered_widths) > HANT_ANUBIS_KNOWN_CONSERVATIVE_MAX_CELLS:
        raise ValueError("Translated Anubis Enemy row exceeds the conservative 336-pixel span")
    if max(rendered_byte_lengths) > HANT_ANUBIS_ROW_BUFFER_BYTES:
        raise ValueError("Translated Anubis Enemy row exceeds the native 0x40-byte copy capacity")
    hant_constraints["max_rendered_glyph_cells"] = max(rendered_widths)
    hant_constraints["max_rendered_row_bytes_including_nul"] = max(rendered_byte_lengths)
    rows.extend(hant_translation_rows)

    original_size = len(source)
    output = bytearray(source)
    patched = []
    for row in rows:
        encoded = encode_ps2_english(row["english"]) + b"\0"
        if len(output) & 1:
            output.append(0)
        target_va = ELF_SEGMENT_VA + len(output) - ELF_SEGMENT_FO
        if target_va & 1:
            raise ValueError(f"Misaligned appended text pointer for {row['key']}")
        output.extend(encoded)
        for pointer_offset in row["pointer_offsets"]:
            struct.pack_into("<I", output, pointer_offset, target_va)
        patched.append({
            "key": row["key"],
            "source_offset": hex(row["source_offset"]),
            "pointer_owner_offsets": [hex(offset) for offset in row["pointer_offsets"]],
            "official_record_offset": hex(row["official_record_offset"]),
            "official_english": row["english"],
            "encoded_bytes": len(encoded),
            "glyph_cells": len(row["english"]),
            "target_va": hex(target_va),
        })
    while len(output) & 3:
        output.append(0)
    if len(output) > MAX_ELF_SEGMENT_SIZE:
        raise ValueError("ELF translation segment reserve exceeded")
    struct.pack_into("<I", output, ELF_SEGMENT_HEADER + 16, len(output) - ELF_SEGMENT_FO)

    existing_changes = {
        offset
        for offset, (before, after) in enumerate(zip(source, output[:original_size], strict=True))
        if before != after
    }
    permitted = {
        *range(ELF_SEGMENT_HEADER + 16, ELF_SEGMENT_HEADER + 20),
        *(offset for start, end in PERMITTED_EXISTING_RANGES for offset in range(start, end)),
    }
    if not existing_changes or existing_changes - permitted:
        raise ValueError(f"Unclassified original ELF changes: {sorted(existing_changes - permitted)}")

    result = bytes(output)
    return result, {
        "revision": "r67.15g",
        "status": "DIAGNOSTIC_STATIC_PROLOGUE_TEXT_ONLY",
        "baseline_15f_elf_sha256_for_traceability": BASE_15F_SHA256,
        "source_elf_sha256": _sha(source),
        "candidate_elf_sha256": _sha(result),
        "source_elf_size": original_size,
        "candidate_elf_size": len(result),
        "appended_extent": {"start": hex(original_size), "end_exclusive": hex(len(result))},
        "translation_segment_file_offset": hex(ELF_SEGMENT_FO),
        "translation_segment_va": hex(ELF_SEGMENT_VA),
        "modified_existing_offsets": [hex(offset) for offset in sorted(existing_changes)],
        "permitted_existing_ranges": [
            [hex(start), hex(end)] for start, end in PERMITTED_EXISTING_RANGES
        ],
        "translated_owners": [hex(offset) for offset in sorted(
            pointer for row in rows for pointer in row["pointer_offsets"]
        )],
        "translated_rows": patched,
        "official_corpus_sha256": corpus_sha,
        "optional_hant_anubis_page": {
            "row_count": len(optional_rows),
            "official_exact_match_count": sum(row["official_english"] is not None for row in optional_rows),
            "rows": optional_rows,
            "record_table_file_offset": hex(HANT_ANUBIS_RECORD_TABLE_FILE_OFFSET),
            "consumer_geometry_proven": False,
            **hant_constraints,
            "native_geometry": hant_constraints,
            "packed_description_rows": list(packed_lines),
            "packed_source_row_indices": list(HANT_ANUBIS_PACKED_ROW_INDICES),
            "packed_official_word_stream": packed_word_stream,
            "dynamic_row_indices": list(HANT_ANUBIS_DYNAMIC_ROW_INDICES),
            "native_hierarchy": {
                "mode": HANT_ENEMY_MODE,
                "category": HANT_ENEMY_CATEGORY,
                "record_index": HANT_ANUBIS_INDEX,
                "root_file_offset": hex(HANT_MODE_ROOT_FILE_OFFSET),
                "mode_table_va": hex(_main_va(HANT_ENEMY_CATEGORY_TABLE_FILE_OFFSET)),
                "category_table_file_offset": hex(HANT_ENEMY_CATEGORY_TABLE_FILE_OFFSET),
                "enemy_index_table_file_offset": hex(HANT_ANUBIS_ENEMY_INDEX_TABLE_FILE_OFFSET),
                "record_table_file_offset": hex(HANT_ANUBIS_RECORD_TABLE_FILE_OFFSET),
                "record_terminator_file_offset": hex(HANT_ANUBIS_RECORD_EOF_FILE_OFFSET),
            },
            "native_getter_va": "0x2a9fe0",
            "native_getter_callsite_va": "0x291ec0",
            "getter_call_arguments": "(s4 mode, s3 category, s2 record index)",
            "metadata_getter_va": "0x2aa020",
            "reachability": "optional H.A.N.T. Enemy record exists in mode 2/category 1/index 0; runtime selection not observed",
            "unresolved_reason": (
                "The exact usable frame edge and optional route reachability have not been runtime "
                "observed. The data-only packing uses the existing conservative 336-pixel span and "
                "keeps all fixed source indices and dynamic branches unchanged."
            ),
            "reachability_unknown": True,
            "changed": True,
        },
        "runtime_verified": False,
        "gameplay_approved": False,
    }
