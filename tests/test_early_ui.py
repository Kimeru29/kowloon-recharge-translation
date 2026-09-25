from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tools.adv_layout import ADV_DG_LAYOUT_PATCHES
from tools.early_ui import EARLY_UI_PATCHES, build_early_ui_elf
from tools.menu_ui import MENU_LABELS
from tools.startup_ui import (
    NAME_BLANK_STRING_OFFSET,
    NAME_PROMPT_ARENA_END,
    NAME_PROMPT_ARENA_START,
    NAME_PROMPT_POINTER_TABLE_OFFSET,
    NAME_READING_ARENA_END,
    NAME_READING_ARENA_START,
    NAME_READING_POINTER_OFFSETS,
    NAME_DEFAULT_POINTER_OFFSETS,
    NAME_RUNTIME_POINTER_OFFSETS,
    NAME_FLOW_STATE9_FLAG_OFFSET,
    TITLE_ARENA_END,
    TITLE_ARENA_START,
    TITLE_LOAD_POINTER_OFFSET,
)
from tools.hant_ui import (
    HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET,
    HANT_CONTROLLER_METADATA_RECORDS,
    HANT_POINTER_TABLE_OFFSET,
    HANT_TUTORIAL_DESCRIPTOR_OFFSET,
    HANT_WRAPPED_LINES,
)
from tools.memory_card_ui import MEMORY_CARD_POINTER_ALIASES
from tools.elf_translation_segment import TRANSLATION_SEGMENT_VADDR
from tools.localization import encode_ps2_english
from tests.local_fixtures import require_local_fixture


ELF_PATH = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF_PATH.read_bytes()


class EarlyUiPatchTests(unittest.TestCase):
    def test_manifest_uses_official_title_and_menu_localization(self) -> None:
        actual = {(patch.offset, patch.expected): patch.text for patch in EARLY_UI_PATCHES}
        semantic_menu = {spec.source_offset: spec for spec in MENU_LABELS}

        # Exact title labels are pointer-relocated and tested in test_startup_ui.
        self.assertNotIn((0x5CBDE8, "初めから"), actual)
        self.assertNotIn((0x5CBDF8, "続きから"), actual)
        self.assertEqual("Items", actual[(0x3BC7C8, "アイテム")])
        self.assertEqual("Quests", actual[(0x3BC7D8, "クエスト")])
        self.assertEqual("H.A.N.T", actual[(0x3BC7E8, "Ｈ．Ａ．Ｎ．Ｔ")])
        self.assertEqual("Save & load", actual[(0x3BC7F8, "セーブ＆ロード")])
        self.assertEqual("Leave room", actual[(0x3BC808, "部屋を出る")])
        self.assertEqual("Shop", actual[(0x3BC818, "ショップ")])
        self.assertEqual("Guild site", actual[(0x3BC828, "ギルドサイト")])
        self.assertEqual("Broadband", actual[(0x3BC838, "ブロードバンド")])
        self.assertEqual("Collection", actual[(0x3BC848, "コレクション")])
        self.assertEqual("Next chapter", actual[(0x3BC868, "次の話へ")])
        self.assertEqual("End turn", actual[(0x3BC878, "ターン終了")])
        self.assertEqual("Interior", actual[(0x3BC898, "インテリア")])
        self.assertEqual("None", actual[(0x694180, "なし")])
        self.assertEqual("Map", actual[(0x694188, "マップ")])
        self.assertEqual("Noise", actual[(0x694198, "ノイズ")])
        self.assertEqual("Battle", actual[(0x6941A0, "戦闘")])
        self.assertEqual("relocated", semantic_menu[0x3BC888].storage)
        self.assertEqual((0x3BC8F4,), semantic_menu[0x3BC888].pointer_offsets)
        self.assertEqual("relocated", semantic_menu[0x694190].storage)
        self.assertEqual((0x3BC8B8,), semantic_menu[0x694190].pointer_offsets)
        self.assertEqual("unresolved", semantic_menu[0x3BC858].status)

    def test_build_changes_only_declared_pristine_regions_before_appended_segment(self) -> None:
        result = build_early_ui_elf(RAW)

        allowed = set(range(TITLE_ARENA_START, TITLE_ARENA_END))
        allowed.update(range(TITLE_LOAD_POINTER_OFFSET, TITLE_LOAD_POINTER_OFFSET + 4))
        allowed.update(range(0x6989C0, 0x6989C4))
        allowed.update(range(0x1AC600, 0x1AC604))
        allowed.update(range(NAME_READING_ARENA_START, NAME_READING_ARENA_END))
        allowed.update(range(NAME_PROMPT_ARENA_START, NAME_PROMPT_ARENA_END))
        allowed.update(range(NAME_PROMPT_POINTER_TABLE_OFFSET, NAME_PROMPT_POINTER_TABLE_OFFSET + 8 * 4))
        for off in NAME_READING_POINTER_OFFSETS:
            allowed.update(range(off, off + 4))
        for offsets in NAME_DEFAULT_POINTER_OFFSETS.values():
            for off in offsets:
                allowed.update(range(off, off + 4))
        for offsets in NAME_RUNTIME_POINTER_OFFSETS.values():
            for off in offsets:
                allowed.update(range(off, off + 4))
        # Runtime reading pointers are immediately after the protagonist name pointers.
        allowed.update(range(0x577C68, 0x577C70))
        for patch in EARLY_UI_PATCHES:
            allowed.update(range(patch.offset, patch.offset + patch.capacity))
        # ADV DG horizontal-layout patch and the two proven H.A.N.T leaf descriptors are runtime patches.
        for off, _expected, _replacement in ADV_DG_LAYOUT_PATCHES:
            allowed.update(range(off, off + 4))
        allowed.update(range(HANT_TUTORIAL_DESCRIPTOR_OFFSET, HANT_TUTORIAL_DESCRIPTOR_OFFSET + 4))
        allowed.update(
            range(HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET, HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET + 4)
        )
        allowed.update(range(0x407440, 0x4074AC))
        for offsets in MEMORY_CARD_POINTER_ALIASES.values():
            for off in offsets:
                allowed.update(range(off, off + 4))
        allowed.update(range(NAME_FLOW_STATE9_FLAG_OFFSET, NAME_FLOW_STATE9_FLAG_OFFSET + 4))
        # ELF program header / heap metadata used by the appended translation segment.
        allowed.update(range(0x54, 0x54 + 32))
        allowed.update(range(0x250, 0x254))
        allowed.update(range(0x650014, 0x650018))
        allowed.update(range(0x8030BC, 0x8030C0))

        differences = {index for index, (before, after) in enumerate(zip(RAW, result[:len(RAW)])) if before != after}
        self.assertTrue(differences)
        self.assertTrue(differences <= allowed)

    def test_composite_build_includes_widened_title_backing(self) -> None:
        result = build_early_ui_elf(RAW)
        scale_x, scale_y = struct.unpack_from("<ff", result, 0x6989C0)
        self.assertAlmostEqual(17.0 / 9.0, scale_x, places=6)
        self.assertEqual(1.0, scale_y)
        self.assertEqual(0x2787D748, struct.unpack_from("<I", result, 0x1AC600)[0])

    def test_composite_build_includes_startup_pointer_relocation(self) -> None:
        result = build_early_ui_elf(RAW)
        target_va = struct.unpack_from("<I", result, NAME_PROMPT_POINTER_TABLE_OFFSET)[0]
        target = target_va - 0x00100000 + 0x80
        expected = encode_ps2_english("Enter last name.") + b"\x00"
        self.assertEqual(expected, result[target:target + len(expected)])
        self.assertGreaterEqual(target_va, 0x00100000)


    def test_composite_build_includes_horizontal_adv_layout(self) -> None:
        result = build_early_ui_elf(RAW)
        for offset, _expected, replacement in ADV_DG_LAYOUT_PATCHES:
            self.assertEqual(replacement, struct.unpack_from("<I", result, offset)[0])

        # The source fields and pristine byte-position /2 normalization remain intact.
        for offset in (0x14FA60, 0x14FAA4, 0x14FAA8):
            self.assertEqual(
                struct.unpack_from("<I", RAW, offset)[0],
                struct.unpack_from("<I", result, offset)[0],
            )

    def test_composite_build_moves_hant_text_to_translation_segment(self) -> None:
        result = build_early_ui_elf(RAW)
        self.assertGreater(len(result), len(RAW))

        p_type, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _flags, _align = struct.unpack_from(
            "<IIIIIIII", result, 0x54
        )
        self.assertEqual(1, p_type)
        self.assertEqual(TRANSLATION_SEGMENT_VADDR, p_vaddr)

        table_va = struct.unpack_from("<I", result, HANT_TUTORIAL_DESCRIPTOR_OFFSET)[0]
        self.assertGreaterEqual(table_va, p_vaddr)
        self.assertLess(table_va, p_vaddr + p_filesz)
        table_file = p_offset + table_va - p_vaddr
        for index, english in enumerate(HANT_WRAPPED_LINES):
            target_va = struct.unpack_from("<I", result, table_file + index * 4)[0]
            self.assertGreaterEqual(target_va, p_vaddr)
            self.assertLess(target_va, p_vaddr + p_filesz)
            target_file = p_offset + target_va - p_vaddr
            expected = encode_ps2_english(english, collapse_spaces=False) + b"\x00"
            self.assertEqual(expected, result[target_file:target_file + len(expected)])

        metadata_va = struct.unpack_from("<I", result, HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET)[0]
        self.assertGreaterEqual(metadata_va, p_vaddr)
        self.assertLess(metadata_va, p_vaddr + p_filesz)
        metadata_file = p_offset + metadata_va - p_vaddr
        actual_metadata = tuple(
            struct.unpack_from("<hhhh", result, metadata_file + index * 8)
            for index in range(len(HANT_CONTROLLER_METADATA_RECORDS))
        )
        self.assertEqual(HANT_CONTROLLER_METADATA_RECORDS, actual_metadata)

        self.assertEqual(
            RAW[HANT_POINTER_TABLE_OFFSET:HANT_POINTER_TABLE_OFFSET + 17 * 4],
            result[HANT_POINTER_TABLE_OFFSET:HANT_POINTER_TABLE_OFFSET + 17 * 4],
        )

    def test_unfit_or_unmapped_slots_are_intentionally_unchanged(self) -> None:
        result = build_early_ui_elf(RAW)

        # Official remaster string is 19 ASCII bytes and cannot fit this 16-byte C-string slot.
        self.assertEqual(RAW[0x3BC888:0x3BC898], result[0x3BC888:0x3BC898])
        # No matching official remaster dictionary entry was found for this PS2-only label.
        self.assertEqual(RAW[0x3BC858:0x3BC868], result[0x3BC858:0x3BC868])
        # "Report card" cannot fit the compact 8-byte runtime slot.
        self.assertEqual(RAW[0x694190:0x694198], result[0x694190:0x694198])


if __name__ == "__main__":
    unittest.main()
