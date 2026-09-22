from __future__ import annotations

import struct

from tools.elf_strings import ElfFixedStringPatch, patch_fixed_strings
from tools.localization import encode_ps2_english


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

# English.bytes localizes these exact fourteen source rows to Latin lower/upper
# alphabets plus the listed symbol/digit rows.  The PS2 input routine copies
# exactly two bytes per selected key, so every logical cell remains a wide/JIS
# glyph; unused legacy kana cells become wide spaces rather than ASCII bytes.
_KEYBOARD_LOGICAL_ROWS = (
    "abcde" + " " * 15,
    "fghij" + " " * 15,
    "klmno" + " " * 15,
    "pqrst" + " " * 15,
    "uvwxy" + " " * 15,
    "z+-x/01234" + " " * 10,
    "=.?!" + " " + "56789" + " " * 10,
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
    ElfFixedStringPatch(0x5865F0, 16, "はばき　　　", ""),
    ElfFixedStringPatch(0x586600, 16, "くろう　　　", ""),
    ElfFixedStringPatch(0x586610, 16, "ひゆう　　　", ""),
    ElfFixedStringPatch(0x586620, 16, "たつま　　　", ""),
    # Runtime character-name record 0 (the protagonist).  This separate table
    # is used by the generic character-name lookup (28-byte records); its first
    # record contains surname, given name, and both readings.  English.bytes
    # confirms 葉佩 -> Habaki and 九龍 -> Kuro and suppresses the readings.
    ElfFixedStringPatch(0x695188, 8, "葉佩", "Habaki"),
    ElfFixedStringPatch(0x695190, 8, "九龍", "Kuro"),
    ElfFixedStringPatch(0x695198, 8, "はばき", ""),
    ElfFixedStringPatch(0x6951A0, 8, "くろう", ""),
    # Name-entry/profile prompts (m_name.c data block).
    ElfFixedStringPatch(0x5869C0, 32, "苗字を入力して下さい。", "Enter last name."),
    ElfFixedStringPatch(0x5869E0, 32, "名前を入力して下さい。", "Enter first name."),
    ElfFixedStringPatch(0x586A00, 48, "苗字の読み仮名を入力して下さい。", "Enter reading for last name."),
    ElfFixedStringPatch(0x586A30, 48, "名前の読み仮名を入力して下さい。", "Enter reading for first name."),
    ElfFixedStringPatch(0x586A60, 24, "これでよろしいですか？", "Is this fine?"),
    ElfFixedStringPatch(0x586A78, 24, "は　い／いいえ", "Yes / No"),
    ElfFixedStringPatch(0x586A90, 32, "ライセンスＩＤを照合中です…。", "Verifying license ID..."),
    ElfFixedStringPatch(0x586AB0, 32, "ＩＤの確認を完了しました。", "ID verification complete."),
    # First-dungeon location label.
    ElfFixedStringPatch(
        0x5CCD40,
        64,
        "ヘラクレイオンの神殿（ヘラクレイオンのしんでん）",
        "Heracleion Shrine",
    ),
    # Default protagonist name table; the first runtime pass showed 九龍 in the HUD.
    ElfFixedStringPatch(0x695840, 8, "葉佩　", "Habaki"),
    ElfFixedStringPatch(0x695848, 8, "九龍　", "Kuro"),
    ElfFixedStringPatch(0x695850, 8, "緋勇　", "Hiyuu"),
    ElfFixedStringPatch(0x695858, 8, "龍麻　", "Tatsuma"),
    *KEYBOARD_ROW_PATCHES,
)


def build_startup_ui_elf(raw: bytes) -> bytes:
    return patch_fixed_strings(patch_title_labels(raw), STARTUP_FIXED_PATCHES)
