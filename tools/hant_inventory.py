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
