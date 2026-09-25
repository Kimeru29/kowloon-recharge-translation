from __future__ import annotations

from collections.abc import Sequence
import struct

from tools.elf_translation_segment import TranslationSegmentInfo
from tools.executable_text import RelocatedText, install_executable_text
from tools.hant_layout import HANT_LAYOUT_PROFILE, wrap_hant_text
from tools.localization import encode_ps2_english
from tools.memory_card_ui import relocated_memory_card_entries
from tools.startup_ui import (
    NAME_BLANK_STRING_OFFSET,
    NAME_PROMPT_POINTER_TABLE_OFFSET,
    NAME_PROMPT_TEXTS,
    NAME_READING_PROMPT_SOURCE_OFFSETS,
)


HANT_POINTER_TABLE_OFFSET = 0x5C8C70
# Resolver VA 0x2A9FE0 indexes the mode/page/subpage hierarchy rooted at
# VA 0x006CBAC0. Tuple (4,2,0) resolves through this descriptor slot to the
# pristine tutorial row-pointer table at VA 0x006C8BF0.
HANT_TUTORIAL_DESCRIPTOR_OFFSET = 0x5CBAB0
# Parallel resolver VA 0x2A9FA0 resolves tuple (4,2,0) to the page-specific
# controller metadata list at VA 0x006C8A20 through this independent leaf.
HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET = 0x5CBA60
HANT_CONTROLLER_METADATA_OFFSET = 0x5C8AA0

_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000
_HANT_BLANK_STRING_OFFSET = 0x696038
_HANT_EOF_STRING_OFFSET = 0x69603C
_HANT_METADATA_SCREEN_X_BASE = 73
_HANT_METADATA_SCREEN_Y_BASE = 119
_HANT_TEXT_ORIGIN_Y = 131


def _elf_va(file_offset: int) -> int:
    return _ELF_MAIN_VADDR + file_offset - _ELF_MAIN_FILE_OFFSET


_HANT_PRISTINE_TABLE_VA = _elf_va(HANT_POINTER_TABLE_OFFSET)
_HANT_PRISTINE_CONTROLLER_METADATA_VA = _elf_va(HANT_CONTROLLER_METADATA_OFFSET)
_HANT_BLANK_VA = _elf_va(_HANT_BLANK_STRING_OFFSET)
_HANT_EOF_VA = _elf_va(_HANT_EOF_STRING_OFFSET)


# Exact source records in the PS2 H.A.N.T startup tutorial. This English was
# already accepted by the pre-v11 project from the official remaster corpus;
# Task 6 intentionally did not promote any newly discovered H.A.N.T candidate
# while English.bytes was absent. v11 changes only presentation of this proven
# tutorial wording and keeps all newly discovered unresolved owners pristine.
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

# Preserve the established public mapping/provenance. Runtime no longer points
# these strings one-for-one at the original Japanese rows; HANT_WRAPPED_LINES is
# derived from this wording and installed as a separate EOF-terminated table.
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

# The official strings use six consecutive spaces at each controller insertion:
# one ordinary word separator plus five cells reserved for the icon. Keep the
# semantic five-cell span explicit instead of treating an arbitrary run of spaces
# as an icon placeholder.
_HANT_CONTROLLER_SOURCE_SPANS: dict[int, tuple[int, int]] = {
    9: (10, 15),
    12: (6, 11),
    14: (10, 15),
}


def _wrap_section(text: str, reserved_spans: tuple[tuple[int, int], ...] = ()) -> tuple[str, ...]:
    return wrap_hant_text(text, HANT_LAYOUT_PROFILE.max_cells, reserved_spans)


def _build_wrapped_hant_lines() -> tuple[tuple[str, ...], dict[int, tuple[int, int]]]:
    body = " ".join(HANT_ENGLISH_LINES[index].strip() for index in (2, 3, 4))
    instruction_1 = " ".join(HANT_ENGLISH_LINES[index].strip() for index in (9, 10))
    instruction_2 = " ".join(HANT_ENGLISH_LINES[index].strip() for index in (12, 13))
    instruction_3 = HANT_ENGLISH_LINES[14].strip()

    body_lines = _wrap_section(body)
    instruction_1_lines = _wrap_section(instruction_1, (_HANT_CONTROLLER_SOURCE_SPANS[9],))
    instruction_2_lines = _wrap_section(instruction_2, (_HANT_CONTROLLER_SOURCE_SPANS[12],))
    instruction_3_lines = _wrap_section(instruction_3, (_HANT_CONTROLLER_SOURCE_SPANS[14],))

    if tuple(map(len, (body_lines, instruction_1_lines, instruction_2_lines, instruction_3_lines))) != (5, 3, 3, 2):
        raise ValueError("H.A.N.T wrapping no longer matches the proven 26-cell page geometry")

    # Preserve the original 16 materialized rows plus EOF shape. Row 1 remains
    # blank; the decorative underline is presentation-only and is omitted rather
    # than mutating/truncating its official punctuation. The three controller
    # holes land on rows 8, 11 and 14 and retain their established five-cell gaps.
    lines = (
        HANT_ENGLISH_LINES[0].strip(),
        "",
        *body_lines,
        HANT_ENGLISH_LINES[7].strip(),
        *instruction_1_lines,
        *instruction_2_lines,
        *instruction_3_lines,
    )
    if len(lines) != HANT_LAYOUT_PROFILE.max_rows:
        raise ValueError(f"wrapped H.A.N.T tutorial must materialize 16 rows, got {len(lines)}")

    controller_spans = {
        8: _HANT_CONTROLLER_SOURCE_SPANS[9],
        11: _HANT_CONTROLLER_SOURCE_SPANS[12],
        14: _HANT_CONTROLLER_SOURCE_SPANS[14],
    }
    gap = " " * HANT_LAYOUT_PROFILE.controller_gap_cells
    for row, (start, end) in controller_spans.items():
        if end - start != HANT_LAYOUT_PROFILE.controller_gap_cells or lines[row][start:end] != gap:
            raise ValueError(f"H.A.N.T controller placeholder was not preserved on row {row}")
    return lines, controller_spans


HANT_WRAPPED_LINES, HANT_CONTROLLER_SPANS_BY_ROW = _build_wrapped_hant_lines()


# The page's parallel metadata list has three 8-byte records and a negative
# sentinel. Fields 2/3 are relative coordinates: screen X = 73 + field2 and
# screen Y = 119 + field3. These pristine records align the icons to Japanese
# gaps at rows/columns (9,0), (12,3), (14,0).
HANT_PRISTINE_CONTROLLER_METADATA_RECORDS: tuple[tuple[int, int, int, int], ...] = (
    (0, 5, 10, 201),
    (38, 1, 54, 263),
    (0, 0, 9, 305),
    (-1, -1, -1, -1),
)
_HANT_SOURCE_ICON_POSITIONS = ((9, 0), (12, 3), (14, 0))
_HANT_TARGET_ICON_POSITIONS = ((8, 10), (11, 6), (14, 10))


def _relocated_controller_metadata() -> tuple[tuple[int, int, int, int], ...]:
    records: list[tuple[int, int, int, int]] = []
    advance = HANT_LAYOUT_PROFILE.glyph_advance
    spacing = HANT_LAYOUT_PROFILE.line_spacing
    origin_x = 85.0

    for record, source, target in zip(
        HANT_PRISTINE_CONTROLLER_METADATA_RECORDS[:3],
        _HANT_SOURCE_ICON_POSITIONS,
        _HANT_TARGET_ICON_POSITIONS,
        strict=True,
    ):
        kind, variant, source_field_x, source_field_y = record
        source_row, source_column = source
        target_row, target_column = target

        source_icon_x = _HANT_METADATA_SCREEN_X_BASE + source_field_x
        source_icon_y = _HANT_METADATA_SCREEN_Y_BASE + source_field_y
        source_gap_x = origin_x + source_column * advance
        source_row_y = _HANT_TEXT_ORIGIN_Y + source_row * spacing
        delta_x = source_icon_x - source_gap_x
        delta_y = source_icon_y - source_row_y

        target_icon_x = origin_x + target_column * advance + delta_x
        target_icon_y = _HANT_TEXT_ORIGIN_Y + target_row * spacing + delta_y
        target_field_x = int(round(target_icon_x - _HANT_METADATA_SCREEN_X_BASE))
        target_field_y = int(round(target_icon_y - _HANT_METADATA_SCREEN_Y_BASE))
        records.append((kind, variant, target_field_x, target_field_y))

    records.append(HANT_PRISTINE_CONTROLLER_METADATA_RECORDS[-1])
    return tuple(records)


HANT_CONTROLLER_METADATA_RECORDS = _relocated_controller_metadata()


def _expected_hant_pointer_table() -> tuple[int, ...]:
    values: list[int] = []
    for index in range(17):
        if index in _HANT_SOURCES:
            values.append(_elf_va(_HANT_SOURCES[index][0]))
        elif index == 16:
            values.append(_HANT_EOF_VA)
        else:
            values.append(_HANT_BLANK_VA)
    return tuple(values)


def _read_metadata_records(raw: bytes, offset: int) -> tuple[tuple[int, int, int, int], ...]:
    size = len(HANT_PRISTINE_CONTROLLER_METADATA_RECORDS) * 8
    if offset + size > len(raw):
        raise ValueError("H.A.N.T controller metadata is outside executable")
    return tuple(
        struct.unpack_from("<hhhh", raw, offset + index * 8)
        for index in range(len(HANT_PRISTINE_CONTROLLER_METADATA_RECORDS))
    )


def _validate_source(raw: bytes) -> None:
    for index, (offset, source) in _HANT_SOURCES.items():
        encoded = source.encode("cp932")
        if raw[offset:offset + len(encoded)] != encoded or raw[offset + len(encoded)] != 0:
            raise ValueError(f"H.A.N.T source preimage mismatch for line {index}")

    table_end = HANT_POINTER_TABLE_OFFSET + 17 * 4
    if table_end > len(raw):
        raise ValueError("H.A.N.T pointer table is outside executable")
    actual_table = struct.unpack_from("<17I", raw, HANT_POINTER_TABLE_OFFSET)
    expected_table = _expected_hant_pointer_table()
    if actual_table != expected_table:
        for index, (actual, expected) in enumerate(zip(actual_table, expected_table, strict=True)):
            if actual != expected:
                raise ValueError(
                    f"H.A.N.T pointer preimage mismatch for line {index}: "
                    f"expected {expected:#x}, got {actual:#x}"
                )
        raise ValueError("H.A.N.T pointer table preimage mismatch")

    if HANT_TUTORIAL_DESCRIPTOR_OFFSET + 4 > len(raw):
        raise ValueError("H.A.N.T tutorial descriptor is outside executable")
    descriptor = struct.unpack_from("<I", raw, HANT_TUTORIAL_DESCRIPTOR_OFFSET)[0]
    if descriptor != _HANT_PRISTINE_TABLE_VA:
        raise ValueError(
            "H.A.N.T tutorial descriptor preimage mismatch: "
            f"expected {_HANT_PRISTINE_TABLE_VA:#x}, got {descriptor:#x}"
        )

    metadata_records = _read_metadata_records(raw, HANT_CONTROLLER_METADATA_OFFSET)
    if metadata_records != HANT_PRISTINE_CONTROLLER_METADATA_RECORDS:
        raise ValueError("H.A.N.T controller metadata preimage mismatch")

    if HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET + 4 > len(raw):
        raise ValueError("H.A.N.T controller metadata descriptor is outside executable")
    metadata_descriptor = struct.unpack_from("<I", raw, HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET)[0]
    if metadata_descriptor != _HANT_PRISTINE_CONTROLLER_METADATA_VA:
        raise ValueError(
            "H.A.N.T controller metadata descriptor preimage mismatch: "
            f"expected {_HANT_PRISTINE_CONTROLLER_METADATA_VA:#x}, got {metadata_descriptor:#x}"
        )


_NAME_READING_PROMPT_INDICES = (2, 3)


def _encoded_wide(text: str) -> bytes:
    return encode_ps2_english(text, collapse_spaces=False) + b"\x00"


def _controller_metadata_bytes() -> bytes:
    return b"".join(struct.pack("<hhhh", *record) for record in HANT_CONTROLLER_METADATA_RECORDS)


def _base_relocated_entries(raw: bytes) -> tuple[RelocatedText, ...]:
    entries: list[RelocatedText] = []
    for index in _NAME_READING_PROMPT_INDICES:
        entries.append(
            RelocatedText(
                key=f"name_prompt_{index}",
                encoded=_encoded_wide(NAME_PROMPT_TEXTS[index]),
                pointer_offsets=(NAME_PROMPT_POINTER_TABLE_OFFSET + index * 4,),
            )
        )

    entries.extend(
        RelocatedText(f"hant_row_{index}", _encoded_wide(text), ())
        for index, text in enumerate(HANT_WRAPPED_LINES)
    )
    # The translated table is patched with the final row VAs after the one PT_LOAD
    # installation. Its 68-byte placeholder preserves the old payload geometry.
    entries.append(
        RelocatedText(
            "hant_table",
            b"\x00" * ((len(HANT_WRAPPED_LINES) + 1) * 4),
            (HANT_TUTORIAL_DESCRIPTOR_OFFSET,),
        )
    )
    entries.append(
        RelocatedText(
            "hant_controller_metadata",
            _controller_metadata_bytes(),
            (HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET,),
        )
    )
    entries.extend(relocated_memory_card_entries(raw))
    return tuple(entries)


def _validate_name_prompt_preimages(raw: bytes) -> None:
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


def patch_hant_tutorial(
    raw: bytes,
    *,
    reserve_size: int = 0x100000,
    extra_entries: Sequence[RelocatedText] = (),
) -> tuple[bytes, TranslationSegmentInfo]:
    """Install all proven shared executable text through one translation PT_LOAD.

    ``extra_entries`` lets the composite early-UI build append independently
    validated relocation classes (currently long command-menu labels) without a
    second translation-segment installation. The default preserves the exact
    pre-Task-9 name/H.A.N.T./memory-card payload for byte-regression tests.
    """

    _validate_source(raw)
    _validate_name_prompt_preimages(raw)

    entries = (*_base_relocated_entries(raw), *tuple(extra_entries))
    installed = install_executable_text(raw, entries, reserve_size=reserve_size)

    table_va = installed.target_vas["hant_table"]
    metadata_va = installed.target_vas["hant_controller_metadata"]
    if table_va & 3 or metadata_va & 3:
        raise ValueError("H.A.N.T structured translation payload lost word alignment")

    result = bytearray(installed.raw)
    table_file = installed.info.file_offset + (table_va - installed.info.segment_vaddr)
    for index in range(len(HANT_WRAPPED_LINES)):
        struct.pack_into("<I", result, table_file + index * 4, installed.target_vas[f"hant_row_{index}"])
    struct.pack_into("<I", result, table_file + len(HANT_WRAPPED_LINES) * 4, _HANT_EOF_VA)

    return bytes(result), installed.info
