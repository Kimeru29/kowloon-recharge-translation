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
    NAME_PROMPT_POINTER_TABLE_OFFSET,
    NAME_PROMPT_TEXTS,
    NAME_READING_POINTER_OFFSETS,
    NAME_BLANK_STRING_OFFSET,
    NAME_DEFAULT_POINTER_OFFSETS,
    NAME_RUNTIME_POINTER_OFFSETS,
    NAME_WIDE_TEXTS,
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
            # Record 0 of the runtime character-name table is the protagonist.
            # It is separately referenced by the generic character-name lookup,
            # so startup must localize it as well as the m_name default table.
            0x5CCD40: ("ヘラクレイオンの神殿（ヘラクレイオンのしんでん）", "Heracleion Shrine"),
        }
        keyboard_offsets = {0x586650 + index * 0x30 for index in range(14)}
        self.assertEqual(set(expected) | keyboard_offsets, set(by_offset))
        for offset, (source, english) in expected.items():
            patch = by_offset[offset]
            self.assertEqual(source, patch.expected)
            self.assertEqual(english, patch.text)
            self.assertEqual("ps2-wide-fixed", patch.encoding)


    def test_name_prompts_and_names_share_wide_relocation_arenas(self) -> None:
        result = build_startup_ui_elf(RAW)

        blank_va = _elf_va(NAME_BLANK_STRING_OFFSET)
        # Reading-default pointers and the two reading prompts are suppressed in
        # the official English flow instead of consuming translation storage.
        for pointer_offset in NAME_READING_POINTER_OFFSETS:
            self.assertEqual(blank_va, struct.unpack_from("<I", result, pointer_offset)[0])
        for prompt_index in (2, 3):
            pointer_offset = NAME_PROMPT_POINTER_TABLE_OFFSET + prompt_index * 4
            self.assertEqual(blank_va, struct.unpack_from("<I", result, pointer_offset)[0])

        # The six visible prompts resolve to exact official English as wide JIS.
        for index in (0, 1, 4, 5, 6, 7):
            english = NAME_PROMPT_TEXTS[index]
            pointer_offset = NAME_PROMPT_POINTER_TABLE_OFFSET + index * 4
            target_va = struct.unpack_from("<I", result, pointer_offset)[0]
            target = target_va - 0x00100000 + 0x80
            encoded = encode_ps2_english(english) + b"\x00"
            self.assertEqual(encoded, result[target:target + len(encoded)])

        # Both m_name defaults and the generic ADV character-name lookup must
        # point at the same relocated wide names.  No ASCII is written into the
        # original fixed records.
        resolved: dict[str, int] = {}
        for name, pointer_offsets in NAME_DEFAULT_POINTER_OFFSETS.items():
            for pointer_offset in pointer_offsets:
                target_va = struct.unpack_from("<I", result, pointer_offset)[0]
                target = target_va - 0x00100000 + 0x80
                encoded = encode_ps2_english(name) + b"\x00"
                self.assertEqual(encoded, result[target:target + len(encoded)])
                resolved.setdefault(name, target_va)
                self.assertEqual(resolved[name], target_va)
        for name, pointer_offsets in NAME_RUNTIME_POINTER_OFFSETS.items():
            for pointer_offset in pointer_offsets:
                self.assertEqual(resolved[name], struct.unpack_from("<I", result, pointer_offset)[0])

        self.assertEqual({"Habaki", "Kuro", "Hiyuu", "Tatsuma"}, set(NAME_WIDE_TEXTS))
        self.assertEqual(RAW[0x695188:0x6951A8], result[0x695188:0x6951A8])
        self.assertEqual(RAW[0x695840:0x695860], result[0x695840:0x695860])

    def test_english_name_flow_skips_ps2_kana_reading_editor(self) -> None:
        result = build_startup_ui_elf(RAW)

        # The state dispatcher calls the same transition routine twice.  State 9
        # originally passes flag 0 (enter kana-reading editor), while state 11
        # passes flag 1 (commit/finalize).  English must reuse flag 1 at state 9
        # because the remaster suppresses the kana reading buffers.
        self.assertEqual(0x24050001, struct.unpack_from("<I", result, 0x186A68)[0])
        self.assertEqual(0x0C0A1788, struct.unpack_from("<I", result, 0x186A6C)[0])
        self.assertEqual(0x24050001, struct.unpack_from("<I", result, 0x186A8C)[0])
        self.assertEqual(0x0C0A1788, struct.unpack_from("<I", result, 0x186A90)[0])

    def test_name_flow_patch_fails_closed_on_dispatcher_drift(self) -> None:
        tampered = bytearray(RAW)
        tampered[0x186A68] ^= 1
        with self.assertRaisesRegex(ValueError, "name.*flow|Name.*flow"):
            build_startup_ui_elf(bytes(tampered))

    def test_name_keyboard_uses_ps2_adapted_latin_rows_with_two_byte_cell_geometry(self) -> None:
        result = build_startup_ui_elf(RAW)
        expected_rows = (
            "abcdeABCDE" + " " * 10,
            "fghijFGHIJ" + " " * 10,
            "klmnoKLMNO" + " " * 10,
            "pqrstPQRST" + " " * 10,
            "uvwxyUVWXY" + " " * 10,
            "z+-x/Z+-X/0123456789",
            "=.?!" + " " + "=.?!" + " " + " " * 10,
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

    def test_ps2_accessible_keyboard_rows_include_both_letter_cases(self) -> None:
        result = build_startup_ui_elf(RAW)
        visible = []
        for index in range(7):
            field = result[0x586650 + index * 0x30:0x586650 + (index + 1) * 0x30]
            for logical_index in range(20):
                storage_index = logical_index + logical_index // 5
                visible.append(field[storage_index * 2:storage_index * 2 + 2].decode("cp932"))
        normalized = unicodedata.normalize("NFKC", "".join(visible))
        for char in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
            self.assertIn(char, normalized)

    def test_build_is_fail_closed_and_changes_only_declared_startup_regions(self) -> None:
        result = build_startup_ui_elf(RAW)
        self.assertEqual(len(RAW), len(result))

        allowed = set(range(TITLE_ARENA_START, TITLE_ARENA_END))
        allowed.update(range(TITLE_LOAD_POINTER_OFFSET, TITLE_LOAD_POINTER_OFFSET + 4))
        allowed.update(range(0x5865F0, 0x586630))
        allowed.update(range(0x586630, 0x586650))
        allowed.update(range(0x5869C0, 0x586AF0))
        allowed.update(range(0x577C60, 0x577C78))
        allowed.update(range(0x186A68, 0x186A6C))
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
