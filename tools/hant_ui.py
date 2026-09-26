from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
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
# Mode-4 tutorial row constructor at VA 0x2908E8. Pristine style 0 is 16x18;
# existing style 1 is 12x12 and reduces English glyph advance without a global
# font change or injected call path.
HANT_TUTORIAL_FONT_STYLE_OFFSET = 0x190968
_HANT_TUTORIAL_FONT_STYLE_PRISTINE_WORD = 0x0000282D  # move a1,zero
_HANT_TUTORIAL_FONT_STYLE_ENGLISH_WORD = 0x24050001   # addiu a1,zero,1
# VA 0x2907E4 materializes the page-local float stride used by
# Y = 131 + stride * row. r4 runtime proved 21px still exceeds the visible
# tutorial budget, so r5 tightens only this page to 18px.
HANT_TUTORIAL_ROW_SPACING_OFFSET = 0x190864
_HANT_TUTORIAL_ROW_SPACING_PRISTINE_WORD = 0x3C0241A8  # lui v0,0x41A8 => 21.0f
_HANT_TUTORIAL_ROW_SPACING_ENGLISH_WORD = 0x3C024190   # lui v0,0x4190 => 18.0f

_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000
_HANT_BLANK_STRING_OFFSET = 0x696038
_HANT_EOF_STRING_OFFSET = 0x69603C
_HANT_METADATA_SCREEN_X_BASE = 73
_HANT_METADATA_SCREEN_Y_BASE = 119
_HANT_TEXT_ORIGIN_Y = 131


@dataclass(frozen=True)
class HantChromeLabel:
    key: str
    source_offset: int
    pointer_offset: int
    source_text: str
    english: str
    provenance: str


@dataclass(frozen=True)
class HantHelpTopic:
    key: str
    source_offset: int
    pointer_offset: int
    source_text: str
    english: str
    provenance: str = "semantic"


# Runtime ownership is proven independently of translation provenance: the seven
# pointers at file 0x586D20 are indexed by the live H.A.N.T. chrome renderer at
# VA 0x2881B0/0x2881C0. The owned remaster extraction does not expose the
# localized TextAsset that would establish exact official wording, so these are
# deliberately classified as semantic translations rather than official text.
# Preserve the original corner-bracket chrome while translating the labels.
HANT_CHROME_LABELS: tuple[HantChromeLabel, ...] = (
    HantChromeLabel("main_menu", 0x586CB0, 0x586D20, "【メインメニュー】", "【Main Menu】", "semantic"),
    HantChromeLabel("mail", 0x586CC8, 0x586D24, "【メール】", "【Mail】", "semantic"),
    HantChromeLabel("dictionary", 0x586CD8, 0x586D28, "【用語辞典】", "【Dictionary】", "semantic"),
    HantChromeLabel("enemy", 0x695888, 0x586D2C, "【敵】", "【Enemy】", "semantic"),
    HantChromeLabel("memo", 0x586CE8, 0x586D30, "【睡院メモ】", "【Memo】", "semantic"),
    HantChromeLabel("help", 0x586CF8, 0x586D34, "【ヘルプ】", "【Help】", "semantic"),
    HantChromeLabel("config", 0x586D08, 0x586D38, "【コンフィグ】", "【Config】", "semantic"),
)


# The Help index shown in the H.A.N.T screenshot is a separate 15-entry pointer
# table at file 0x587840. Each pointer resolves one visible Japanese topic label;
# preserving the source strings while relocating those exact aliases keeps the
# owner boundary explicit. Wording is semantic because the current owned PS4
# extraction no longer exposes the localized bundle/TextAsset for this screen.
HANT_HELP_TOPICS: tuple[HantHelpTopic, ...] = (
    HantHelpTopic("hant_functions", 0x5876E0, 0x587840, "Ｈ．Ａ．Ｎ．Ｔの機能", "H.A.N.T Functions"),
    HantHelpTopic("command_thumbnails", 0x587700, 0x587844, "コマンドサムネイル", "Command Thumbnails"),
    HantHelpTopic("your_room", 0x587718, 0x587848, "自室について", "About Your Room"),
    HantHelpTopic("shopping_site", 0x587730, 0x58784C, "ショッピングサイト", "Shopping Site"),
    HantHelpTopic("guild_site", 0x587748, 0x587850, "ギルドサイト", "Guild Site"),
    HantHelpTopic("shop", 0x587758, 0x587854, "売店について", "About the Shop"),
    HantHelpTopic("item_screen", 0x587770, 0x587858, "アイテム画面について", "Item Screen"),
    HantHelpTopic("using_items", 0x587790, 0x58785C, "アイテムの使い方", "Using Items"),
    HantHelpTopic("carrying_items", 0x5877A8, 0x587860, "アイテムの携行", "Carrying Items"),
    HantHelpTopic("equipping_items", 0x5877B8, 0x587864, "アイテムの装備", "Equipping Items"),
    HantHelpTopic("recycling", 0x5877D0, 0x587868, "リサイクルについて", "Recycling"),
    HantHelpTopic("item_synthesis", 0x5877E8, 0x58786C, "アイテムの調合", "Item Synthesis"),
    HantHelpTopic("ammunition", 0x5877F8, 0x587870, "弾薬について", "Ammunition"),
    HantHelpTopic("level_up", 0x587810, 0x587874, "レベルアップしたら", "When You Level Up"),
    HantHelpTopic("save_load", 0x587828, 0x587878, "セーブ＆ロード", "Save & Load"),
)


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
    boot_heading_lines = _wrap_section(HANT_ENGLISH_LINES[7].strip())
    instruction_1_lines = _wrap_section(instruction_1, (_HANT_CONTROLLER_SOURCE_SPANS[9],))
    instruction_2_lines = _wrap_section(instruction_2, (_HANT_CONTROLLER_SOURCE_SPANS[12],))
    instruction_3_lines = _wrap_section(instruction_3, (_HANT_CONTROLLER_SOURCE_SPANS[14],))

    if tuple(map(len, (body_lines, boot_heading_lines, instruction_1_lines, instruction_2_lines, instruction_3_lines))) != (5, 1, 3, 3, 2):
        raise ValueError("H.A.N.T wrapping no longer matches the 12px/28-cell tutorial profile")

    # Keep all accepted instructional wording while dropping only the redundant
    # standalone H.A.N.T heading and decorative separator. The existing 12px font
    # style fits the text in 14 rows, leaving two rows of headroom under the
    # renderer's hard 16-row cap instead of clipping the final instruction.
    lines = (
        *body_lines,
        *boot_heading_lines,
        *instruction_1_lines,
        *instruction_2_lines,
        *instruction_3_lines,
    )
    if len(lines) != 14 or len(lines) > HANT_LAYOUT_PROFILE.max_rows:
        raise ValueError(f"wrapped H.A.N.T tutorial must materialize 14 rows, got {len(lines)}")

    controller_spans = {
        6: _HANT_CONTROLLER_SOURCE_SPANS[9],
        9: _HANT_CONTROLLER_SOURCE_SPANS[12],
        12: _HANT_CONTROLLER_SOURCE_SPANS[14],
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
_HANT_TARGET_ICON_POSITIONS = ((6, 10), (9, 6), (12, 10))
_HANT_PRISTINE_GLYPH_ADVANCE = 16.0
_HANT_PRISTINE_LINE_SPACING = 21.0


def _relocated_controller_metadata() -> tuple[tuple[int, int, int, int], ...]:
    records: list[tuple[int, int, int, int]] = []
    target_advance = HANT_LAYOUT_PROFILE.glyph_advance
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
        source_gap_x = origin_x + source_column * _HANT_PRISTINE_GLYPH_ADVANCE
        source_row_y = _HANT_TEXT_ORIGIN_Y + source_row * _HANT_PRISTINE_LINE_SPACING
        delta_x = source_icon_x - source_gap_x
        delta_y = source_icon_y - source_row_y

        target_icon_x = origin_x + target_column * target_advance + delta_x
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
    if HANT_TUTORIAL_ROW_SPACING_OFFSET + 4 > len(raw):
        raise ValueError("H.A.N.T renderer spacing preimage is outside executable")
    actual_spacing = struct.unpack_from("<I", raw, HANT_TUTORIAL_ROW_SPACING_OFFSET)[0]
    if actual_spacing != _HANT_TUTORIAL_ROW_SPACING_PRISTINE_WORD:
        raise ValueError(
            "H.A.N.T renderer spacing preimage mismatch: "
            f"expected {_HANT_TUTORIAL_ROW_SPACING_PRISTINE_WORD:#010x}, got {actual_spacing:#010x}"
        )

    if HANT_TUTORIAL_FONT_STYLE_OFFSET + 4 > len(raw):
        raise ValueError("H.A.N.T renderer style preimage is outside executable")
    actual_style = struct.unpack_from("<I", raw, HANT_TUTORIAL_FONT_STYLE_OFFSET)[0]
    if actual_style != _HANT_TUTORIAL_FONT_STYLE_PRISTINE_WORD:
        raise ValueError(
            "H.A.N.T renderer style preimage mismatch: "
            f"expected {_HANT_TUTORIAL_FONT_STYLE_PRISTINE_WORD:#010x}, got {actual_style:#010x}"
        )

    for spec in HANT_CHROME_LABELS:
        encoded = spec.source_text.encode("cp932")
        if (
            spec.source_offset + len(encoded) >= len(raw)
            or raw[spec.source_offset:spec.source_offset + len(encoded)] != encoded
            or raw[spec.source_offset + len(encoded)] != 0
        ):
            raise ValueError(f"H.A.N.T chrome source preimage mismatch: {spec.key}")
        if spec.pointer_offset + 4 > len(raw):
            raise ValueError(f"H.A.N.T chrome pointer is outside executable: {spec.key}")
        expected_va = _elf_va(spec.source_offset)
        actual_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
        if actual_va != expected_va:
            raise ValueError(
                f"H.A.N.T chrome pointer preimage mismatch for {spec.key}: "
                f"expected {expected_va:#x}, got {actual_va:#x}"
            )

    for spec in HANT_HELP_TOPICS:
        encoded = spec.source_text.encode("cp932")
        if (
            spec.source_offset + len(encoded) >= len(raw)
            or raw[spec.source_offset:spec.source_offset + len(encoded)] != encoded
            or raw[spec.source_offset + len(encoded)] != 0
        ):
            raise ValueError(f"H.A.N.T help-topic source preimage mismatch: {spec.key}")
        if spec.pointer_offset + 4 > len(raw):
            raise ValueError(f"H.A.N.T help-topic pointer is outside executable: {spec.key}")
        expected_va = _elf_va(spec.source_offset)
        actual_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
        if actual_va != expected_va:
            raise ValueError(
                f"H.A.N.T help-topic pointer preimage mismatch for {spec.key}: "
                f"expected {expected_va:#x}, got {actual_va:#x}"
            )

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
    # The translated pointer table itself requires 4-byte alignment, while the
    # shared allocator intentionally guarantees only 2-byte string alignment.
    # Keep one explicit H.A.N.T.-owned 2-byte pad before the structured table;
    # the translated string payload is only 2-byte aligned while this table must
    # remain 4-byte aligned. The fail-closed
    # alignment check below still guards future row-shape drift.
    entries.append(RelocatedText("hant_table_alignment", b"\x00\x00", ()))
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
    entries.extend(
        RelocatedText(
            key=f"hant_chrome_{spec.key}",
            encoded=_encoded_wide(spec.english),
            pointer_offsets=(spec.pointer_offset,),
        )
        for spec in HANT_CHROME_LABELS
    )
    entries.extend(
        RelocatedText(
            key=f"hant_help_{spec.key}",
            encoded=_encoded_wide(spec.english),
            pointer_offsets=(spec.pointer_offset,),
        )
        for spec in HANT_HELP_TOPICS
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
    second translation-segment installation. The base payload includes the
    accepted name/H.A.N.T./memory-card classes plus the separately owned semantic
    H.A.N.T. chrome labels.
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
    struct.pack_into(
        "<I",
        result,
        HANT_TUTORIAL_ROW_SPACING_OFFSET,
        _HANT_TUTORIAL_ROW_SPACING_ENGLISH_WORD,
    )
    struct.pack_into(
        "<I",
        result,
        HANT_TUTORIAL_FONT_STYLE_OFFSET,
        _HANT_TUTORIAL_FONT_STYLE_ENGLISH_WORD,
    )
    table_file = installed.info.file_offset + (table_va - installed.info.segment_vaddr)
    for index in range(len(HANT_WRAPPED_LINES)):
        struct.pack_into("<I", result, table_file + index * 4, installed.target_vas[f"hant_row_{index}"])
    struct.pack_into("<I", result, table_file + len(HANT_WRAPPED_LINES) * 4, _HANT_EOF_VA)

    return bytes(result), installed.info
