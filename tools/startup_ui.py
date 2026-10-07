from __future__ import annotations

import struct

from tools.elf_strings import ElfFixedStringPatch, patch_fixed_strings
from tools.localization import encode_ps2_english
from tools.title_layout import patch_title_layout


# The title renderer consumes two-byte JIS glyph codes.  The pristine executable
# stores two 16-byte C-string slots followed by eight zero bytes, then a separate
# long blank string.  Together the first two slots + padding form a 40-byte arena:
# enough for exact NUL-terminated "New Game" and "Load Game" when the second
# pointer is moved four bytes forward.  This preserves the third pointer/blank
# string entirely.
TITLE_ARENA_START = 0x5CBDE8
TITLE_ARENA_END = 0x5CBE10
TITLE_NEW_GAME_START = TITLE_ARENA_START
TITLE_LOAD_START = 0x5CBDFC
TITLE_POINTER_TABLE_OFFSET = 0x5CBE50
TITLE_LOAD_POINTER_OFFSET = 0x5CBE54
_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000


def _elf_va(file_offset: int) -> int:
    return _ELF_MAIN_VADDR + file_offset - _ELF_MAIN_FILE_OFFSET


def _expected_title_arena() -> bytes:
    result = bytearray(TITLE_ARENA_END - TITLE_ARENA_START)
    first = "初めから".encode("cp932") + b"\x00"
    second = "続きから".encode("cp932") + b"\x00"
    result[0:len(first)] = first
    second_offset = 0x5CBDF8 - TITLE_ARENA_START
    result[second_offset:second_offset + len(second)] = second
    return bytes(result)


def patch_title_labels(raw: bytes) -> bytes:
    if TITLE_ARENA_END > len(raw) or TITLE_LOAD_POINTER_OFFSET + 4 > len(raw):
        raise ValueError("Title patch is outside executable")

    expected_arena = _expected_title_arena()
    actual_arena = raw[TITLE_ARENA_START:TITLE_ARENA_END]
    if actual_arena != expected_arena:
        raise ValueError(
            "Source preimage mismatch for title string arena: "
            f"expected {expected_arena.hex()}, got {actual_arena.hex()}"
        )

    expected_new_ptr = _elf_va(0x5CBDE8)
    expected_load_ptr = _elf_va(0x5CBDF8)
    actual_new_ptr = struct.unpack_from("<I", raw, TITLE_POINTER_TABLE_OFFSET)[0]
    actual_load_ptr = struct.unpack_from("<I", raw, TITLE_LOAD_POINTER_OFFSET)[0]
    if actual_new_ptr != expected_new_ptr or actual_load_ptr != expected_load_ptr:
        raise ValueError(
            "Source preimage mismatch for title pointer table: "
            f"expected {expected_new_ptr:#x}/{expected_load_ptr:#x}, "
            f"got {actual_new_ptr:#x}/{actual_load_ptr:#x}"
        )

    new_game = encode_ps2_english("New Game") + b"\x00"
    load_game = encode_ps2_english("Load Game") + b"\x00"
    if TITLE_NEW_GAME_START + len(new_game) > TITLE_LOAD_START:
        raise ValueError("New Game title text overlaps relocated Load Game text")
    if TITLE_LOAD_START + len(load_game) > TITLE_ARENA_END:
        raise ValueError("Load Game title text does not fit title arena")

    result = bytearray(raw)
    result[TITLE_ARENA_START:TITLE_ARENA_END] = b"\x00" * (TITLE_ARENA_END - TITLE_ARENA_START)
    result[TITLE_NEW_GAME_START:TITLE_NEW_GAME_START + len(new_game)] = new_game
    result[TITLE_LOAD_START:TITLE_LOAD_START + len(load_game)] = load_game
    struct.pack_into("<I", result, TITLE_LOAD_POINTER_OFFSET, _elf_va(TITLE_LOAD_START))
    return bytes(result)


# Name-entry/profile text is rendered through the same two-byte glyph path as
# the title.  The original m_name module has only 272 bytes for its eight
# Japanese prompts, while the exact official English needs 326 bytes including
# terminators.  Four kana-reading defaults become unused in the English flow;
# each has one unique pointer, so redirecting those pointers to the module's
# existing blank wide string safely reclaims their 64-byte block.  Together
# these two module-local arenas hold the exact English without borrowing
# unrelated executable storage.
NAME_READING_ARENA_START = 0x5865F0
NAME_READING_ARENA_END = 0x586630
NAME_READING_POINTER_OFFSETS = (0x586638, 0x58663C, 0x586648, 0x58664C)
NAME_BLANK_STRING_OFFSET = 0x586B98
NAME_PROMPT_ARENA_START = 0x5869C0
NAME_PROMPT_ARENA_END = 0x586AD0
NAME_PROMPT_POINTER_TABLE_OFFSET = 0x586AD0
NAME_PROMPT_TEXTS = (
    "Enter last name.",
    "Enter first name.",
    "Enter reading for last name.",
    "Enter reading for first name.",
    "Is this fine?",
    "Yes / No",
    "Verifying license ID...",
    "ID verification complete.",
)
_NAME_PROMPT_SOURCES = (
    (0x5869C0, "苗字を入力して下さい。"),
    (0x5869E0, "名前を入力して下さい。"),
    (0x586A00, "苗字の読み仮名を入力して下さい。"),
    (0x586A30, "名前の読み仮名を入力して下さい。"),
    (0x586A60, "これでよろしいですか？"),
    (0x586A78, "は　い／いいえ"),
    (0x586A90, "ライセンスＩＤを照合中です…。"),
    (0x586AB0, "ＩＤの確認を完了しました。"),
)
_NAME_READING_SOURCES = (
    (0x5865F0, "はばき　　　"),
    (0x586600, "くろう　　　"),
    (0x586610, "ひゆう　　　"),
    (0x586620, "たつま　　　"),
)
# The original 272-byte prompt arena cannot hold all eight wide English prompts
# while the 64-byte reading-default arena is needed for the four wide Latin
# default names.  This first pass therefore packs six prompts locally and stages
# prompt indices 2/3 on the existing blank string.  The final shared translation
# segment pass relocates those two official reading prompts out-of-line.
_NAME_VISIBLE_PROMPT_INDICES = (0, 1, 4, 5, 6, 7)
_NAME_READING_PROMPT_INDICES = (2, 3)
NAME_READING_PROMPT_SOURCE_OFFSETS = {2: 0x586A00, 3: 0x586A30}
NAME_WIDE_TEXTS = ("Habaki", "Kuro", "Hiyuu", "Tatsuma")
NAME_DEFAULT_POINTER_OFFSETS = {
    "Habaki": (0x586630,),
    "Kuro": (0x586634,),
    "Hiyuu": (0x586640,),
    "Tatsuma": (0x586644,),
}
_NAME_DEFAULT_SOURCES = {
    "Habaki": (0x695840, "葉佩　"),
    "Kuro": (0x695848, "九龍　"),
    "Hiyuu": (0x695850, "緋勇　"),
    "Tatsuma": (0x695858, "龍麻　"),
}
# Generic ADV character-name lookup: record zero is the protagonist.  Both
# references to the surname and the one reference to the given name must move
# with the m_name defaults or later dialogue/HUD code will still see Japanese.
NAME_RUNTIME_POINTER_OFFSETS = {
    "Habaki": (0x577C60, 0x577C74),
    "Kuro": (0x577C64,),
}
_NAME_RUNTIME_SOURCES = {
    "Habaki": (0x695188, "葉佩"),
    "Kuro": (0x695190, "九龍"),
}
_NAME_RUNTIME_READING_POINTERS = (
    (0x577C68, 0x695198, "はばき"),
    (0x577C6C, 0x6951A0, "くろう"),
)

# The PS2 state dispatcher invokes the same M_Name transition routine from
# state 9 and state 11.  State 9 passes 0 and enters the kana-reading editor;
# state 11 passes 1 and commits/finalizes.  The official English remaster
# suppresses the reading buffers, so English reuses the already-existing flag-1
# path at state 9 instead of entering the PS2-only kana pass.
NAME_FLOW_STATE9_FLAG_OFFSET = 0x186A68
_NAME_FLOW_STATE9_CALL_OFFSET = 0x186A6C
_NAME_FLOW_STATE11_FLAG_OFFSET = 0x186A8C
_NAME_FLOW_STATE11_CALL_OFFSET = 0x186A90
_NAME_FLOW_FLAG_ZERO_WORD = 0x0000282D  # daddu a1, zero, zero
_NAME_FLOW_FLAG_ONE_WORD = 0x24050001   # addiu a1, zero, 1
_NAME_FLOW_TRANSITION_JAL_WORD = 0x0C0A1788  # jal 0x285e20

# The M_Name prompt renderer uses one 16-pixel two-byte glyph font object and
# repositions it per state before selecting text from NAME_PROMPT_TEXTS. Japanese
# fixed X origins are visibly right-shifted with English. Entries 0/1 and 2/3
# share one state X, so use the midpoint of their two exact centered origins
# (maximum 8px error); single prompts use their exact 512px-view centers. The
# Yes/No line uses the second prompt object created at file 0x181888.
NAME_PROMPT_LAYOUT_PATCHES: tuple[tuple[int, int, int], ...] = (
    (0x1819DC, 0x3C02432C, 0x3C0242F8),  # Enter last/first name: 172 -> 124
    (0x181A68, 0x3C024304, 0x3C0241E0),  # reading prompts: 132 -> 28
    (0x181AF4, 0x3C024324, 0x3C024318),  # Is this fine?: 164 -> 152
    (0x181888, 0x3C024350, 0x3C024340),  # Yes / No: 208 -> 192
    (0x181B70, 0x3C02430C, 0x3C024290),  # Verifying license ID...: 140 -> 72
    (0x181EAC, 0x3C02431C, 0x3C024260),  # ID verification complete.: 156 -> 56
)

# The confirmation focus renderer has separate geometry/color ownership from the
# static Yes / No prompt. In Japanese, selected Yes covered two glyph children
# and child 2 was the separator, so the renderer explicitly reset child 2 to the
# base color. English puts the third `Yes` glyph at child 2, so resetting that
# child now erases `s`; the separator-side child starts at child 3. Runtime r9 shows
# exactly that failure. Move the selected-Yes X with the accepted prompt shift and
# reset child 3 instead. The No branch at 0x181DC8 (X=272) is already runtime-good.
NAME_CONFIRMATION_FOCUS_PATCHES: tuple[tuple[int, int, int], ...] = (
    (0x181D0C, 0x3C024350, 0x3C024340),  # Yes focus X: 208 -> 192
    (0x181D9C, 0x24050002, 0x24050003),  # separator child: 2 -> 3
)
_NAME_CONFIRMATION_NO_FOCUS_X_OFFSET = 0x181DC8
_NAME_CONFIRMATION_NO_FOCUS_X_WORD = 0x3C024388  # 272.0f, preserve


def patch_name_prompt_layout(raw: bytes) -> bytes:
    for offset, expected, _replacement in NAME_PROMPT_LAYOUT_PATCHES:
        if offset + 4 > len(raw):
            raise ValueError("Name-prompt layout patch is outside executable")
        actual = struct.unpack_from("<I", raw, offset)[0]
        if actual != expected:
            raise ValueError(
                f"Name-prompt layout preimage mismatch at {offset:#x}: "
                f"expected {expected:#010x}, got {actual:#010x}"
            )

    result = bytearray(raw)
    for offset, _expected, replacement in NAME_PROMPT_LAYOUT_PATCHES:
        struct.pack_into("<I", result, offset, replacement)
    return bytes(result)


def patch_name_confirmation_focus(raw: bytes) -> bytes:
    for offset, expected, _replacement in NAME_CONFIRMATION_FOCUS_PATCHES:
        if offset + 4 > len(raw):
            raise ValueError("Name confirmation focus patch is outside executable")
        actual = struct.unpack_from("<I", raw, offset)[0]
        if actual != expected:
            raise ValueError(
                f"Name confirmation focus preimage mismatch at {offset:#x}: "
                f"expected {expected:#010x}, got {actual:#010x}"
            )
    if struct.unpack_from("<I", raw, _NAME_CONFIRMATION_NO_FOCUS_X_OFFSET)[0] != _NAME_CONFIRMATION_NO_FOCUS_X_WORD:
        raise ValueError("Name confirmation focus preimage mismatch for accepted No geometry")

    result = bytearray(raw)
    for offset, _expected, replacement in NAME_CONFIRMATION_FOCUS_PATCHES:
        struct.pack_into("<I", result, offset, replacement)
    return bytes(result)


def patch_name_entry_flow(raw: bytes) -> bytes:
    expected = (
        (NAME_FLOW_STATE9_FLAG_OFFSET, _NAME_FLOW_FLAG_ZERO_WORD),
        (_NAME_FLOW_STATE9_CALL_OFFSET, _NAME_FLOW_TRANSITION_JAL_WORD),
        (_NAME_FLOW_STATE11_FLAG_OFFSET, _NAME_FLOW_FLAG_ONE_WORD),
        (_NAME_FLOW_STATE11_CALL_OFFSET, _NAME_FLOW_TRANSITION_JAL_WORD),
    )
    for offset, word in expected:
        if offset + 4 > len(raw):
            raise ValueError("Name-entry flow patch is outside executable")
        actual = struct.unpack_from("<I", raw, offset)[0]
        if actual != word:
            raise ValueError(
                f"Name-entry flow preimage mismatch at {offset:#x}: "
                f"expected {word:#010x}, got {actual:#010x}"
            )

    result = bytearray(raw)
    struct.pack_into("<I", result, NAME_FLOW_STATE9_FLAG_OFFSET, _NAME_FLOW_FLAG_ONE_WORD)
    return bytes(result)


def _validate_c_string(raw: bytes, offset: int, expected: str) -> None:
    encoded = expected.encode("cp932")
    if raw[offset:offset + len(encoded)] != encoded or raw[offset + len(encoded)] != 0:
        raise ValueError(f"Source preimage mismatch at {offset:#x}: expected {expected!r}")


def _pack_named_wide_strings(
    result: bytearray,
    start: int,
    end: int,
    items: tuple[tuple[object, str], ...],
) -> dict[object, int]:
    result[start:end] = b"\x00" * (end - start)
    cursor = start
    targets: dict[object, int] = {}
    for key, text in items:
        if cursor & 1:
            cursor += 1
        payload = encode_ps2_english(text, collapse_spaces=False) + b"\x00"
        if cursor + len(payload) > end:
            raise ValueError("Translated name-entry strings do not fit proven module-local arenas")
        result[cursor:cursor + len(payload)] = payload
        targets[key] = cursor
        cursor += len(payload)
    return targets


def patch_name_prompt_arena(raw: bytes) -> bytes:
    if NAME_BLANK_STRING_OFFSET + 13 > len(raw):
        raise ValueError("Name-entry relocation patch is outside executable")

    for (source_offset, source), pointer_offset in zip(
        _NAME_READING_SOURCES, NAME_READING_POINTER_OFFSETS, strict=True
    ):
        _validate_c_string(raw, source_offset, source)
        if struct.unpack_from("<I", raw, pointer_offset)[0] != _elf_va(source_offset):
            raise ValueError(f"Source preimage mismatch for reading pointer at {pointer_offset:#x}")

    for index, (source_offset, source) in enumerate(_NAME_PROMPT_SOURCES):
        _validate_c_string(raw, source_offset, source)
        pointer_offset = NAME_PROMPT_POINTER_TABLE_OFFSET + index * 4
        if struct.unpack_from("<I", raw, pointer_offset)[0] != _elf_va(source_offset):
            raise ValueError(f"Source preimage mismatch for prompt pointer at {pointer_offset:#x}")

    for name, (source_offset, source) in _NAME_DEFAULT_SOURCES.items():
        _validate_c_string(raw, source_offset, source)
        for pointer_offset in NAME_DEFAULT_POINTER_OFFSETS[name]:
            if struct.unpack_from("<I", raw, pointer_offset)[0] != _elf_va(source_offset):
                raise ValueError(f"Source preimage mismatch for default-name pointer at {pointer_offset:#x}")

    for name, (source_offset, source) in _NAME_RUNTIME_SOURCES.items():
        _validate_c_string(raw, source_offset, source)
        for pointer_offset in NAME_RUNTIME_POINTER_OFFSETS[name]:
            if struct.unpack_from("<I", raw, pointer_offset)[0] != _elf_va(source_offset):
                raise ValueError(f"Source preimage mismatch for runtime-name pointer at {pointer_offset:#x}")
    for pointer_offset, source_offset, source in _NAME_RUNTIME_READING_POINTERS:
        _validate_c_string(raw, source_offset, source)
        if struct.unpack_from("<I", raw, pointer_offset)[0] != _elf_va(source_offset):
            raise ValueError(f"Source preimage mismatch for runtime-reading pointer at {pointer_offset:#x}")

    blank = "　　　　　　".encode("cp932") + b"\x00"
    if raw[NAME_BLANK_STRING_OFFSET:NAME_BLANK_STRING_OFFSET + len(blank)] != blank:
        raise ValueError("Source preimage mismatch for m_name blank wide string")

    result = bytearray(raw)
    blank_va = _elf_va(NAME_BLANK_STRING_OFFSET)
    for pointer_offset in NAME_READING_POINTER_OFFSETS:
        struct.pack_into("<I", result, pointer_offset, blank_va)
    for prompt_index in _NAME_READING_PROMPT_INDICES:
        struct.pack_into(
            "<I", result, NAME_PROMPT_POINTER_TABLE_OFFSET + prompt_index * 4, blank_va
        )
    for pointer_offset, _, _ in _NAME_RUNTIME_READING_POINTERS:
        struct.pack_into("<I", result, pointer_offset, blank_va)

    name_targets = _pack_named_wide_strings(
        result,
        NAME_READING_ARENA_START,
        NAME_READING_ARENA_END,
        tuple((name, name) for name in NAME_WIDE_TEXTS),
    )
    prompt_targets = _pack_named_wide_strings(
        result,
        NAME_PROMPT_ARENA_START,
        NAME_PROMPT_ARENA_END,
        tuple((index, NAME_PROMPT_TEXTS[index]) for index in _NAME_VISIBLE_PROMPT_INDICES),
    )

    for index, target in prompt_targets.items():
        struct.pack_into(
            "<I", result, NAME_PROMPT_POINTER_TABLE_OFFSET + int(index) * 4, _elf_va(target)
        )
    for name, target in name_targets.items():
        target_va = _elf_va(target)
        for pointer_offset in NAME_DEFAULT_POINTER_OFFSETS[str(name)]:
            struct.pack_into("<I", result, pointer_offset, target_va)
        for pointer_offset in NAME_RUNTIME_POINTER_OFFSETS.get(str(name), ()):
            struct.pack_into("<I", result, pointer_offset, target_va)

    return bytes(result)

def _keyboard_storage_text(logical_cells: str) -> str:
    """Lay 20 logical keys into the PS2 keyboard's four five-key groups."""

    if len(logical_cells) != 20:
        raise ValueError("Keyboard rows must contain exactly 20 logical cells")
    # Input code addresses logical column N at N + floor(N / 5), so each
    # five-key group is followed by one non-selectable visual spacer.
    return " ".join(logical_cells[index:index + 5] for index in range(0, 20, 5))


_KEYBOARD_SOURCES = (
    "あいうえお　や　ゆ　よ　がぎぐげご　ＡＢＣＤＥ",
    "かきくけこ　らりるれろ　ざじずぜぞ　ＦＧＨＩＪ",
    "さしすせそ　わ　　　を　だぢづでど　ＫＬＭＮＯ",
    "たちつてと　んっゃゅょ　ばびぶべぼ　ＰＱＲＳＴ",
    "なにぬねの　ぁぃぅぇぉ　ぱぴぷぺぽ　ＵＶＷＸＹ",
    "はひふへほ　０１２３４　＃＄％＆＊　Ｚ＋－×÷",
    "まみむめも　５６７８９　々ー　　　　＝・？！　",
    "アイウエオ　ヤ　ユ　ヨ　ガギグゲゴ　ＡＢＣＤＥ",
    "カキクケコ　ラリルレロ　ザジズゼゾ　ＦＧＨＩＪ",
    "サシスセソ　ワ　　　ヲ　ダヂヅデド　ＫＬＭＮＯ",
    "タチツテト　ンッャュョ　バビブベボ　ＰＱＲＳＴ",
    "ナニヌネノ　ァィゥェォ　パピプペポ　ＵＶＷＸＹ",
    "ハヒフヘホ　０１２３４　＃＄％＆＊　Ｚ＋－×÷",
    "マミムメモ　５６７８９　々ー　　　　＝・？！　",
)

# English.bytes supplies the Latin lower/upper character repertoire used here.
# Static tracing proves this PS2 build only indexes row pointers 0..6; there is no
# R1/L1 switch to rows 7..13.  The reachable seven rows therefore fold lower and
# upper case together while preserving the PS2 two-byte/JIS cell geometry.
_KEYBOARD_LOGICAL_ROWS = (
    # PS2 m_name only indexes rows 0..6.  Unlike the remaster, it has no
    # reachable 7..13 page, so fold upper-case keys into the accessible page.
    "abcdeABCDE" + " " * 10,
    "fghijFGHIJ" + " " * 10,
    "klmnoKLMNO" + " " * 10,
    "pqrstPQRST" + " " * 10,
    "uvwxyUVWXY" + " " * 10,
    "z+-x/Z+-X/0123456789",
    "=.?!" + " " + "=.?!" + " " + " " * 10,
    # Preserve the remaster-derived second page data even though the PS2 code
    # never indexes it; keeping it translated avoids reintroducing kana if a
    # later control-flow patch makes the page reachable.
    "ABCDE" + " " * 15,
    "FGHIJ" + " " * 15,
    "KLMNO" + " " * 15,
    "PQRST" + " " * 15,
    "UVWXY" + " " * 15,
    "Z+-X/01234" + " " * 10,
    "=.?!" + " " + "56789" + " " * 10,
)

KEYBOARD_ROW_PATCHES: tuple[ElfFixedStringPatch, ...] = tuple(
    ElfFixedStringPatch(
        0x586650 + index * 0x30,
        48,
        source,
        _keyboard_storage_text(logical),
        encoding="ps2-wide-fixed",
    )
    for index, (source, logical) in enumerate(
        zip(_KEYBOARD_SOURCES, _KEYBOARD_LOGICAL_ROWS, strict=True)
    )
)


# Official remaster dictionary values for all currently identified runtime text
# on the path from New Game through arrival at the first DG00 dialogue.
STARTUP_FIXED_PATCHES: tuple[ElfFixedStringPatch, ...] = (
    # Official English remaster suppresses the default-name kana readings.
    # Keep the PS2 fixed 16-byte fields but blank their visible contents.
    # Runtime character-name record 0 (the protagonist).  This separate table
    # is used by the generic character-name lookup (28-byte records); its first
    # record contains surname, given name, and both readings.  English.bytes
    # confirms 葉佩 -> Habaki and 九龍 -> Kuro and suppresses the readings.
    # Name-entry/profile prompts (m_name.c data block).
    # First-dungeon location label.
    ElfFixedStringPatch(
        0x5CCD40,
        64,
        "ヘラクレイオンの神殿（ヘラクレイオンのしんでん）",
        "Heracleion Shrine",
        encoding="ps2-wide-fixed",
    ),
    # Default protagonist name table; the first runtime pass showed 九龍 in the HUD.
    *KEYBOARD_ROW_PATCHES,
)


def build_startup_ui_elf(raw: bytes) -> bytes:
    laid_out = patch_title_layout(raw)
    titled = patch_title_labels(laid_out)
    relocated = patch_name_prompt_arena(titled)
    flowed = patch_name_entry_flow(relocated)
    prompt_layout = patch_name_prompt_layout(flowed)
    confirmation_focus = patch_name_confirmation_focus(prompt_layout)
    return patch_fixed_strings(confirmation_focus, STARTUP_FIXED_PATCHES)
