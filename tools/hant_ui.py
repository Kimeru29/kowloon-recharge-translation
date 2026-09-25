from __future__ import annotations

import struct

from tools.elf_translation_segment import (
    TRANSLATION_SEGMENT_VADDR,
    TranslationSegmentInfo,
    install_translation_segment,
)
from tools.localization import encode_ps2_english
from tools.memory_card_ui import (
    MEMORY_CARD_MESSAGES,
    MEMORY_CARD_POINTER_ALIASES,
    MEMORY_CARD_POINTER_TABLE_OFFSET,
    encode_memory_card_english,
    validate_memory_card_sources,
)
from tools.startup_ui import (
    NAME_BLANK_STRING_OFFSET,
    NAME_PROMPT_POINTER_TABLE_OFFSET,
    NAME_PROMPT_TEXTS,
    NAME_READING_PROMPT_SOURCE_OFFSETS,
)


HANT_POINTER_TABLE_OFFSET = 0x5C8C70
_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000


def _elf_va(file_offset: int) -> int:
    return _ELF_MAIN_VADDR + file_offset - _ELF_MAIN_FILE_OFFSET


# Exact source records in the PS2 H.A.N.T startup tutorial.  Most English is
# taken verbatim from English.bytes; index 12 uses the official remaster's
# semantically equivalent 方向ボタン record because re-charge's PS2 text says
# 方向キー at that one site.
_HANT_SOURCES: dict[int, tuple[int, str]] = {
    0: (0x5C8AC0, "　　　＜Ｈ．Ａ．Ｎ．Ｔについて＞"),
    2: (0x5C8AF0, "Ｈ．Ａ．Ｎ．Ｔは、"),
    3: (0x5C8B10, "探索をサポートする小型情報端末です。"),
    4: (0x5C8B40, "≪操作方法≫や≪情報≫の確認ができます。"),
    7: (0x5C8B70, "　　　Ｈ．Ａ．Ｎ．Ｔの起動方法"),
    8: (0x5C8B90, "　　　￣￣￣￣￣￣￣￣￣￣￣￣"),
    9: (0x5C8BB0, "　ＳＥＬＥＣＴボタンを押して"),
    10: (0x5C8BD0, "コマンドサムネイルを呼び出します。"),
    12: (0x5C8C00, "次に、　方向キーで"),
    13: (0x5C8C20, "「Ｈ．Ａ．Ｎ．Ｔ」を選択し"),
    14: (0x5C8C40, "　ボタンを押すと起動させることができます。"),
}

HANT_ENGLISH_LINES: dict[int, str] = {
    0: "                           H.A.N.T",
    2: "The H.A.N.T is a mini info device designed",
    3: "to support exploration. You can review",
    4: "game controls and other info here.",
    7: "     Booting Up the H.A.N.T",
    8: "     -----------------------------",
    9: "Press the      button to bring up the",
    10: "command thumbnails.",
    12: "Next,      press the directional buttons",
    13: "to select the H.A.N.T",
    14: "Press the      button to boot it up.",
}


def _validate_source(raw: bytes) -> None:
    for index, (offset, source) in _HANT_SOURCES.items():
        encoded = source.encode("cp932")
        if raw[offset:offset + len(encoded)] != encoded or raw[offset + len(encoded)] != 0:
            raise ValueError(f"H.A.N.T source preimage mismatch for line {index}")
        pointer_offset = HANT_POINTER_TABLE_OFFSET + index * 4
        if pointer_offset + 4 > len(raw):
            raise ValueError("H.A.N.T pointer table is outside executable")
        actual = struct.unpack_from("<I", raw, pointer_offset)[0]
        expected = _elf_va(offset)
        if actual != expected:
            raise ValueError(
                f"H.A.N.T pointer preimage mismatch for line {index}: "
                f"expected {expected:#x}, got {actual:#x}"
            )


_NAME_READING_PROMPT_INDICES = (2, 3)


def _append_encoded(payload: bytearray, encoded: bytes) -> int:
    if len(payload) & 1:
        payload.append(0)
    offset = len(payload)
    payload.extend(encoded)
    payload.append(0)
    return offset


def _append_wide(payload: bytearray, text: str) -> int:
    return _append_encoded(payload, encode_ps2_english(text, collapse_spaces=False))


def _build_payload() -> tuple[bytes, dict[int, int], dict[int, int], dict[int, int]]:
    payload = bytearray()
    name_prompt_offsets: dict[int, int] = {}
    for index in _NAME_READING_PROMPT_INDICES:
        name_prompt_offsets[index] = _append_wide(payload, NAME_PROMPT_TEXTS[index])

    hant_offsets: dict[int, int] = {}
    for index in sorted(HANT_ENGLISH_LINES):
        hant_offsets[index] = _append_wide(payload, HANT_ENGLISH_LINES[index])

    memory_card_offsets: dict[int, int] = {}
    for index in sorted(MEMORY_CARD_MESSAGES):
        english = MEMORY_CARD_MESSAGES[index][2]
        memory_card_offsets[index] = _append_encoded(payload, encode_memory_card_english(english))
    return bytes(payload), name_prompt_offsets, hant_offsets, memory_card_offsets


def patch_hant_tutorial(
    raw: bytes,
    *,
    reserve_size: int = 0x100000,
) -> tuple[bytes, TranslationSegmentInfo]:
    _validate_source(raw)
    validate_memory_card_sources(raw)
    blank_va = _elf_va(NAME_BLANK_STRING_OFFSET)
    for index in _NAME_READING_PROMPT_INDICES:
        pointer_offset = NAME_PROMPT_POINTER_TABLE_OFFSET + index * 4
        if pointer_offset + 4 > len(raw):
            raise ValueError("Name-reading prompt pointer table is outside executable")
        actual = struct.unpack_from("<I", raw, pointer_offset)[0]
        pristine_va = _elf_va(NAME_READING_PROMPT_SOURCE_OFFSETS[index])
        if actual not in (pristine_va, blank_va):
            raise ValueError(
                f"Name-reading prompt {index} preimage mismatch: "
                f"expected pristine/staged pointer {pristine_va:#x}/{blank_va:#x}, got {actual:#x}"
            )

    payload, name_prompt_offsets, hant_offsets, memory_card_offsets = _build_payload()
    expanded, info = install_translation_segment(raw, payload, reserve_size=reserve_size)
    if info.segment_vaddr != TRANSLATION_SEGMENT_VADDR:
        raise ValueError("Unexpected translation-segment base")

    result = bytearray(expanded)
    for index, payload_offset in name_prompt_offsets.items():
        struct.pack_into(
            "<I",
            result,
            NAME_PROMPT_POINTER_TABLE_OFFSET + index * 4,
            info.segment_vaddr + payload_offset,
        )
    for index, payload_offset in hant_offsets.items():
        struct.pack_into(
            "<I",
            result,
            HANT_POINTER_TABLE_OFFSET + index * 4,
            info.segment_vaddr + payload_offset,
        )
    for index, payload_offset in memory_card_offsets.items():
        target_va = info.segment_vaddr + payload_offset
        struct.pack_into(
            "<I",
            result,
            MEMORY_CARD_POINTER_TABLE_OFFSET + index * 4,
            target_va,
        )
        for alias_offset in MEMORY_CARD_POINTER_ALIASES.get(index, ()):
            struct.pack_into("<I", result, alias_offset, target_va)
    return bytes(result), info
