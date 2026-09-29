from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import struct
from typing import Iterable


HANT_POINTER_TABLE_OFFSET = 0x5C8C70
_HANT_POINTER_COUNT = 17
_HANT_CONTROL_INDICES = frozenset({1, 5, 6, 11, 15, 16})
_MAIN_FILE_START = 0x80
_MAIN_FILE_END = 0x699200
_MAIN_VADDR = 0x00100000
_HANT_TOKEN = "Ｈ．Ａ．Ｎ．Ｔ"
_MAX_STRING_BYTES = 512
_HELP_MODE = 4
_HELP_CATEGORY_COUNTS = (20, 20, 15)
_HELP_TEXT_ROOT_VA = 0x006CBAC0
_HELP_METADATA_ROOT_VA = 0x006CBAA0
_HELP_EOF_VA = 0x00795FBC
_MAX_HELP_BODY_ROWS = 128
_MAX_HELP_METADATA_RECORDS = 64


@dataclass(frozen=True)
class HantTextEntry:
    key: str
    source_offset: int
    pointer_offsets: tuple[int, ...]
    source_text: str
    official_english: str | None
    classification: str
    owner: str
    evidence: str


@dataclass(frozen=True)
class HantHelpBodyOwner:
    mode: int
    category_index: int
    topic_index: int
    text_descriptor_offset: int
    text_table_offset: int
    row_count: int
    metadata_descriptor_offset: int
    metadata_offset: int
    metadata_record_count: int


def _va_to_file(va: int) -> int | None:
    offset = _MAIN_FILE_START + (va - _MAIN_VADDR)
    if _MAIN_FILE_START <= offset < _MAIN_FILE_END:
        return offset
    return None


def _file_to_va(offset: int) -> int:
    return _MAIN_VADDR + offset - _MAIN_FILE_START


def _read_cp932_c_string(raw: bytes, offset: int) -> str | None:
    if not (_MAIN_FILE_START <= offset < min(len(raw), _MAIN_FILE_END)):
        return None
    end_limit = min(len(raw), _MAIN_FILE_END, offset + _MAX_STRING_BYTES)
    end = raw.find(b"\x00", offset, end_limit)
    if end < 0:
        return None
    try:
        return raw[offset:end].decode("cp932")
    except UnicodeDecodeError:
        return None


def _official_match(
    source_text: str,
    english_rows: tuple[tuple[str, str, int], ...] | None,
    *,
    allow_direction_semantic: bool = False,
) -> tuple[str | None, str, str]:
    if english_rows is None:
        return None, "unresolved", "official English corpus unavailable"

    exact = [(value, offset) for key, value, offset in english_rows if key == source_text]
    if len(exact) == 1:
        value, offset = exact[0]
        return value, "official_exact", f"exact English.bytes key at {offset:#x}"
    if len(exact) > 1:
        return None, "unresolved", f"ambiguous exact English.bytes key ({len(exact)} matches)"

    if allow_direction_semantic and "方向キー" in source_text:
        remaster_key = source_text.replace("方向キー", "方向ボタン")
        semantic = [(value, offset) for key, value, offset in english_rows if key == remaster_key]
        if len(semantic) == 1:
            value, offset = semantic[0]
            return (
                value,
                "official_semantic",
                f"documented PS2 方向キー / remaster 方向ボタン semantic match at {offset:#x}",
            )
        if len(semantic) > 1:
            return None, "unresolved", f"ambiguous 方向ボタン English.bytes key ({len(semantic)} matches)"

    return None, "unresolved", "no exact official English.bytes key"


def _tutorial_entries(
    raw: bytes,
    english_rows: tuple[tuple[str, str, int], ...] | None,
) -> tuple[HantTextEntry, ...]:
    table_end = HANT_POINTER_TABLE_OFFSET + _HANT_POINTER_COUNT * 4
    if table_end > len(raw):
        raise ValueError("H.A.N.T tutorial pointer table is outside executable")

    entries: list[HantTextEntry] = []
    for index in range(_HANT_POINTER_COUNT):
        pointer_offset = HANT_POINTER_TABLE_OFFSET + index * 4
        target_va = struct.unpack_from("<I", raw, pointer_offset)[0]
        source_offset = _va_to_file(target_va)
        if source_offset is None:
            raise ValueError(f"H.A.N.T tutorial pointer {index} targets outside main executable")
        source_text = _read_cp932_c_string(raw, source_offset)
        if source_text is None:
            raise ValueError(f"H.A.N.T tutorial pointer {index} does not resolve to CP932 C-string")

        if index in _HANT_CONTROL_INDICES:
            official_english = None
            classification = "control"
            evidence = (
                f"tutorial pointer-table slot {index} at {pointer_offset:#x}; "
                f"control/sentinel target {source_offset:#x}"
            )
        else:
            official_english, classification, match_evidence = _official_match(
                source_text,
                english_rows,
                allow_direction_semantic=index == 12,
            )
            evidence = (
                f"tutorial pointer-table slot {index} at {pointer_offset:#x} -> {source_offset:#x}; "
                f"{match_evidence}"
            )

        entries.append(
            HantTextEntry(
                key=f"hant_tutorial_{index:02d}",
                source_offset=source_offset,
                pointer_offsets=(pointer_offset,),
                source_text=source_text,
                official_english=official_english,
                classification=classification,
                owner="hant_tutorial",
                evidence=evidence,
            )
        )
    return tuple(entries)


def _candidate_entries(
    raw: bytes,
    tutorial_offsets: frozenset[int],
    english_rows: tuple[tuple[str, str, int], ...] | None,
) -> tuple[HantTextEntry, ...]:
    refs_by_target: dict[int, list[int]] = defaultdict(list)
    main_end = min(len(raw), _MAIN_FILE_END)
    if main_end < _MAIN_FILE_END:
        raise ValueError("H.A.N.T inventory requires the complete main executable section")

    for pointer_offset in range(_MAIN_FILE_START, main_end - 3, 4):
        target_va = struct.unpack_from("<I", raw, pointer_offset)[0]
        target_offset = _va_to_file(target_va)
        if target_offset is None or target_offset in tutorial_offsets:
            continue
        source_text = _read_cp932_c_string(raw, target_offset)
        if source_text is None or _HANT_TOKEN not in source_text:
            continue
        refs_by_target[target_offset].append(pointer_offset)

    entries: list[HantTextEntry] = []
    for source_offset in sorted(refs_by_target):
        source_text = _read_cp932_c_string(raw, source_offset)
        assert source_text is not None
        official_english, classification, match_evidence = _official_match(source_text, english_rows)
        pointer_offsets = tuple(sorted(set(refs_by_target[source_offset])))
        refs = ", ".join(f"{offset:#x}" for offset in pointer_offsets)
        entries.append(
            HantTextEntry(
                key=f"hant_candidate_{source_offset:08x}",
                source_offset=source_offset,
                pointer_offsets=pointer_offsets,
                source_text=source_text,
                official_english=official_english,
                classification=classification,
                owner="executable_hant_candidate",
                evidence=(
                    f"pointer-backed executable CP932 string contains {_HANT_TOKEN}; "
                    f"references: {refs}; {match_evidence}"
                ),
            )
        )
    return tuple(entries)


def _read_u32_file(raw: bytes, offset: int, *, owner: str) -> int:
    if offset < _MAIN_FILE_START or offset + 4 > min(len(raw), _MAIN_FILE_END):
        raise ValueError(f"{owner} pointer is outside the main executable: {offset:#x}")
    return struct.unpack_from("<I", raw, offset)[0]


def _help_category_descriptor_base(raw: bytes, root_va: int, category_index: int, *, owner: str) -> int:
    root_offset = _va_to_file(root_va)
    if root_offset is None:
        raise ValueError(f"{owner} root is outside the main executable")
    mode_table_va = _read_u32_file(raw, root_offset + _HELP_MODE * 4, owner=owner)
    mode_table_offset = _va_to_file(mode_table_va)
    if mode_table_offset is None:
        raise ValueError(f"{owner} mode-{_HELP_MODE} table is outside the main executable")
    category_table_va = _read_u32_file(raw, mode_table_offset + category_index * 4, owner=owner)
    category_table_offset = _va_to_file(category_table_va)
    if category_table_offset is None:
        raise ValueError(f"{owner} category {category_index} table is outside the main executable")
    return category_table_offset


def _count_help_body_rows(raw: bytes, table_offset: int) -> int:
    for row_index in range(_MAX_HELP_BODY_ROWS + 1):
        pointer_offset = table_offset + row_index * 4
        target_va = _read_u32_file(raw, pointer_offset, owner="H.A.N.T Help body row table")
        if target_va == _HELP_EOF_VA:
            return row_index
        if _va_to_file(target_va) is None:
            raise ValueError(
                "H.A.N.T Help body row targets outside the main executable: "
                f"table={table_offset:#x}, row={row_index}, va={target_va:#x}"
            )
    raise ValueError(f"H.A.N.T Help body table at {table_offset:#x} lacks EOF within bounded row budget")


def _count_help_metadata_records(raw: bytes, metadata_offset: int) -> int:
    for record_index in range(_MAX_HELP_METADATA_RECORDS + 1):
        offset = metadata_offset + record_index * 8
        if offset < _MAIN_FILE_START or offset + 8 > min(len(raw), _MAIN_FILE_END):
            raise ValueError(f"H.A.N.T Help metadata leaves the main executable at {offset:#x}")
        record = struct.unpack_from("<hhhh", raw, offset)
        if record[0] < 0:
            return record_index
    raise ValueError(
        f"H.A.N.T Help metadata at {metadata_offset:#x} lacks a negative sentinel within bounded record budget"
    )


def inventory_hant_help_bodies(raw: bytes) -> tuple[HantHelpBodyOwner, ...]:
    """Inventory the bounded 55 selected-page owners behind H.A.N.T. Help.

    Runtime selection passes ``(mode=4, category, topic)`` to the generic page
    constructor. Text and auxiliary metadata are separate three-level pointer
    trees rooted at ``0x006CBAC0`` and ``0x006CBAA0`` respectively. This
    inventory follows those trees only for the statically proven Help category
    cardinalities (20 ADV, 20 exploration, 15 other) and requires every text
    leaf to reach EOF plus every metadata leaf to reach its negative sentinel.
    """

    main_end = min(len(raw), _MAIN_FILE_END)
    if main_end < _MAIN_FILE_END:
        raise ValueError("H.A.N.T Help body inventory requires the complete main executable section")

    entries: list[HantHelpBodyOwner] = []
    for category_index, topic_count in enumerate(_HELP_CATEGORY_COUNTS):
        text_descriptor_base = _help_category_descriptor_base(
            raw,
            _HELP_TEXT_ROOT_VA,
            category_index,
            owner="H.A.N.T Help text",
        )
        metadata_descriptor_base = _help_category_descriptor_base(
            raw,
            _HELP_METADATA_ROOT_VA,
            category_index,
            owner="H.A.N.T Help metadata",
        )
        for topic_index in range(topic_count):
            text_descriptor_offset = text_descriptor_base + topic_index * 4
            text_table_va = _read_u32_file(raw, text_descriptor_offset, owner="H.A.N.T Help text descriptor")
            text_table_offset = _va_to_file(text_table_va)
            if text_table_offset is None:
                raise ValueError(
                    f"H.A.N.T Help text leaf ({category_index},{topic_index}) targets outside main executable"
                )

            metadata_descriptor_offset = metadata_descriptor_base + topic_index * 4
            metadata_va = _read_u32_file(
                raw,
                metadata_descriptor_offset,
                owner="H.A.N.T Help metadata descriptor",
            )
            metadata_offset = _va_to_file(metadata_va)
            if metadata_offset is None:
                raise ValueError(
                    f"H.A.N.T Help metadata leaf ({category_index},{topic_index}) targets outside main executable"
                )

            entries.append(
                HantHelpBodyOwner(
                    mode=_HELP_MODE,
                    category_index=category_index,
                    topic_index=topic_index,
                    text_descriptor_offset=text_descriptor_offset,
                    text_table_offset=text_table_offset,
                    row_count=_count_help_body_rows(raw, text_table_offset),
                    metadata_descriptor_offset=metadata_descriptor_offset,
                    metadata_offset=metadata_offset,
                    metadata_record_count=_count_help_metadata_records(raw, metadata_offset),
                )
            )

    if len(entries) != sum(_HELP_CATEGORY_COUNTS):
        raise ValueError("H.A.N.T Help body inventory cardinality drifted")
    if len({entry.text_descriptor_offset for entry in entries}) != len(entries):
        raise ValueError("H.A.N.T Help body inventory has duplicate text descriptor ownership")
    return tuple(entries)


def inventory_hant_text(
    raw: bytes,
    english_rows: Iterable[tuple[str, str, int]] | None,
) -> tuple[HantTextEntry, ...]:
    """Inventory bounded, pointer-backed H.A.N.T text in the pristine PS2 ELF.

    The known 17-slot tutorial table is authoritative for tutorial ownership.
    Outside it, only CP932 strings containing the fullwidth H.A.N.T token and
    reached by aligned executable pointers are surfaced as candidates. Generic
    words such as ``情報`` are deliberately insufficient evidence on their own.
    """

    rows = None if english_rows is None else tuple(english_rows)
    tutorial = _tutorial_entries(raw, rows)
    tutorial_offsets = frozenset(entry.source_offset for entry in tutorial)
    candidates = _candidate_entries(raw, tutorial_offsets, rows)
    entries = tutorial + candidates
    if len(entries) != len({entry.key for entry in entries}):
        raise ValueError("H.A.N.T inventory produced duplicate stable keys")
    return entries
