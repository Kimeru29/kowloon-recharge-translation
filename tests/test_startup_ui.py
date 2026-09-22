from __future__ import annotations

import struct
import unicodedata
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.localization import encode_ps2_english
from tools.startup_ui import (
    STARTUP_FIXED_PATCHES,
    TITLE_ARENA_END,
    TITLE_ARENA_START,
    TITLE_LOAD_POINTER_OFFSET,
    TITLE_LOAD_START,
    TITLE_NEW_GAME_START,
    TITLE_POINTER_TABLE_OFFSET,
    build_startup_ui_elf,
)


ELF_PATH = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF_PATH.read_bytes()


def _elf_va(file_offset: int) -> int:
    # SLPM_665.11 main PT_LOAD: file 0x80 -> virtual 0x00100000.
    return 0x00100000 + file_offset - 0x80


class StartupUiPatchTests(unittest.TestCase):
    def test_title_uses_exact_official_labels_and_repoints_load_string(self) -> None:
        result = build_startup_ui_elf(RAW)

        new_game = encode_ps2_english("New Game") + b"\x00"
        load_game = encode_ps2_english("Load Game") + b"\x00"
        self.assertEqual(new_game, result[TITLE_NEW_GAME_START:TITLE_NEW_GAME_START + len(new_game)])
        self.assertEqual(load_game, result[TITLE_LOAD_START:TITLE_LOAD_START + len(load_game)])
        self.assertEqual(
            _elf_va(TITLE_NEW_GAME_START),
            struct.unpack_from("<I", result, TITLE_POINTER_TABLE_OFFSET)[0],
        )
        self.assertEqual(
            _elf_va(TITLE_LOAD_START),
            struct.unpack_from("<I", result, TITLE_LOAD_POINTER_OFFSET)[0],
        )
        # The third title-table entry points at a long blank string used by the
        # title UI and must not be consumed as translation storage.
        self.assertEqual(RAW[0x5CBE58:0x5CBE5C], result[0x5CBE58:0x5CBE5C])
        self.assertEqual(RAW[0x5CBE10:0x5CBE50], result[0x5CBE10:0x5CBE50])

    def test_startup_manifest_covers_every_known_pre_dialogue_runtime_string(self) -> None:
        by_offset = {patch.offset: patch for patch in STARTUP_FIXED_PATCHES}
        expected = {
            # The official remaster suppresses the kana readings for the default
            # protagonist name; the PS2 English build does the same.
            0x5865F0: ("はばき　　　", ""),
            0x586600: ("くろう　　　", ""),
            0x586610: ("ひゆう　　　", ""),
            0x586620: ("たつま　　　", ""),
            # Record 0 of the runtime character-name table is the protagonist.
            # It is separately referenced by the generic character-name lookup,
            # so startup must localize it as well as the m_name default table.
            0x695188: ("葉佩", "Habaki"),
            0x695190: ("九龍", "Kuro"),
            0x695198: ("はばき", ""),
            0x6951A0: ("くろう", ""),
            0x5869C0: ("苗字を入力して下さい。", "Enter last name."),
            0x5869E0: ("名前を入力して下さい。", "Enter first name."),
            0x586A00: ("苗字の読み仮名を入力して下さい。", "Enter reading for last name."),
            0x586A30: ("名前の読み仮名を入力して下さい。", "Enter reading for first name."),
            0x586A60: ("これでよろしいですか？", "Is this fine?"),
            0x586A78: ("は　い／いいえ", "Yes / No"),
            0x586A90: ("ライセンスＩＤを照合中です…。", "Verifying license ID..."),
            0x586AB0: ("ＩＤの確認を完了しました。", "ID verification complete."),
            0x5CCD40: ("ヘラクレイオンの神殿（ヘラクレイオンのしんでん）", "Heracleion Shrine"),
            0x695840: ("葉佩　", "Habaki"),
            0x695848: ("九龍　", "Kuro"),
            0x695850: ("緋勇　", "Hiyuu"),
            0x695858: ("龍麻　", "Tatsuma"),
        }
        keyboard_offsets = {0x586650 + index * 0x30 for index in range(14)}
        self.assertEqual(set(expected) | keyboard_offsets, set(by_offset))
        for offset, (source, english) in expected.items():
            patch = by_offset[offset]
            self.assertEqual(source, patch.expected)
            self.assertEqual(english, patch.text)
            self.assertEqual("ascii", patch.encoding)


    def test_name_keyboard_uses_official_latin_rows_with_ps2_two_byte_cell_geometry(self) -> None:
        result = build_startup_ui_elf(RAW)
        expected_rows = (
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
        row_offsets = tuple(0x586650 + index * 0x30 for index in range(14))

        def logical_cells(field: bytes) -> str:
            cells: list[str] = []
            for logical_index in range(20):
                storage_index = logical_index + logical_index // 5
                glyph = field[storage_index * 2:storage_index * 2 + 2]
                self.assertEqual(2, len(glyph))
                cells.append(glyph.decode("cp932"))
            return unicodedata.normalize("NFKC", "".join(cells))

        for offset, expected in zip(row_offsets, expected_rows, strict=True):
            self.assertEqual(expected, logical_cells(result[offset:offset + 48]))

        # The 14-entry row pointer table and 7x20 cursor-map geometry are data
        # structures, not translation strings; the port must not rewrite them.
        self.assertEqual(RAW[0x5868F0:0x586930], result[0x5868F0:0x586930])
        self.assertEqual(RAW[0x586930:0x5869BC], result[0x586930:0x5869BC])

    def test_build_is_fail_closed_and_changes_only_declared_startup_regions(self) -> None:
        result = build_startup_ui_elf(RAW)
        self.assertEqual(len(RAW), len(result))

        allowed = set(range(TITLE_ARENA_START, TITLE_ARENA_END))
        allowed.update(range(TITLE_LOAD_POINTER_OFFSET, TITLE_LOAD_POINTER_OFFSET + 4))
        for patch in STARTUP_FIXED_PATCHES:
            allowed.update(range(patch.offset, patch.offset + patch.capacity))

        changed = {i for i, (before, after) in enumerate(zip(RAW, result)) if before != after}
        self.assertTrue(changed)
        self.assertTrue(changed <= allowed)

        tampered = bytearray(RAW)
        tampered[0x586A90] ^= 0x01
        with self.assertRaisesRegex(ValueError, "(?:Source preimage mismatch|expected source mismatch)"):
            build_startup_ui_elf(bytes(tampered))

    def test_title_arena_layout_fits_without_touching_next_string(self) -> None:
        self.assertLess(TITLE_NEW_GAME_START, TITLE_LOAD_START)
        self.assertLessEqual(
            TITLE_LOAD_START + len(encode_ps2_english("Load Game")) + 1,
            TITLE_ARENA_END,
        )
        self.assertEqual(0x5CBE10, TITLE_ARENA_END)


if __name__ == "__main__":
    unittest.main()
