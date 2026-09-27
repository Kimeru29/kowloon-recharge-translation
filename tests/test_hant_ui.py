from __future__ import annotations

import hashlib
import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.hant_inventory import inventory_hant_text
from tools.hant_layout import HANT_LAYOUT_PROFILE, measured_hant_cells
from tools.hant_ui import (
    HANT_ENGLISH_LINES,
    HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET,
    HANT_CONTROLLER_METADATA_OFFSET,
    HANT_CONTROLLER_METADATA_RECORDS,
    HANT_CONTROLLER_SPANS_BY_ROW,
    HANT_POINTER_TABLE_OFFSET,
    HANT_PRISTINE_CONTROLLER_METADATA_RECORDS,
    HANT_TUTORIAL_DESCRIPTOR_OFFSET,
    HANT_WRAPPED_LINES,
    patch_hant_tutorial,
)
from tools.startup_ui import NAME_PROMPT_POINTER_TABLE_OFFSET, NAME_PROMPT_TEXTS
from tools.localization import encode_ps2_english

ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


def _segment_file_offset(info, va: int) -> int:
    return info.file_offset + (va - info.segment_vaddr)


class HantTutorialTests(unittest.TestCase):
    def test_runtime_corrected_hant_payload_geometry_is_deterministic(self) -> None:
        result, info = patch_hant_tutorial(RAW)

        self.assertEqual(4485, info.payload_size)
        self.assertEqual(
            "6cf9f8d3ee6933d2047603824a60160c9a93fce6685f345ff40896fae0f12dd1",
            hashlib.sha256(result).hexdigest(),
        )
        self.assertEqual(
            info.segment_vaddr,
            struct.unpack_from("<I", result, NAME_PROMPT_POINTER_TABLE_OFFSET + 2 * 4)[0],
        )
        self.assertEqual(
            info.segment_vaddr + 58,
            struct.unpack_from("<I", result, NAME_PROMPT_POINTER_TABLE_OFFSET + 3 * 4)[0],
        )
        self.assertEqual(
            info.segment_vaddr + 716,
            struct.unpack_from("<I", result, HANT_TUTORIAL_DESCRIPTOR_OFFSET)[0],
        )
        self.assertEqual(
            info.segment_vaddr + 776,
            struct.unpack_from("<I", result, HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET)[0],
        )

    def test_repoints_tutorial_descriptor_to_wrapped_translation_table(self) -> None:
        result, info = patch_hant_tutorial(RAW)
        self.assertGreater(len(result), len(RAW))
        self.assertEqual(0x902F00, info.segment_vaddr)

        for index in (2, 3):
            target_va = struct.unpack_from("<I", result, NAME_PROMPT_POINTER_TABLE_OFFSET + index * 4)[0]
            self.assertGreaterEqual(target_va, info.segment_vaddr)
            self.assertLess(target_va, info.segment_vaddr + info.payload_size)
            target_file = _segment_file_offset(info, target_va)
            expected = encode_ps2_english(NAME_PROMPT_TEXTS[index], collapse_spaces=False) + b"\x00"
            self.assertEqual(expected, result[target_file:target_file + len(expected)])

        table_va = struct.unpack_from("<I", result, HANT_TUTORIAL_DESCRIPTOR_OFFSET)[0]
        self.assertGreaterEqual(table_va, info.segment_vaddr)
        self.assertLess(table_va, info.segment_vaddr + info.payload_size)
        table_file = _segment_file_offset(info, table_va)

        self.assertEqual(14, len(HANT_WRAPPED_LINES))
        self.assertEqual("The H.A.N.T is a mini info", HANT_WRAPPED_LINES[0])
        self.assertEqual(
            {6: (10, 15), 9: (6, 11), 12: (10, 15)},
            HANT_CONTROLLER_SPANS_BY_ROW,
        )
        self.assertEqual(
            ((0, 5, 130, 108), (38, 1, 78, 155), (0, 0, 129, 203), (-1, -1, -1, -1)),
            HANT_CONTROLLER_METADATA_RECORDS,
        )
        for index, english in enumerate(HANT_WRAPPED_LINES):
            self.assertLessEqual(measured_hant_cells(english), HANT_LAYOUT_PROFILE.max_cells)
            target_va = struct.unpack_from("<I", result, table_file + index * 4)[0]
            self.assertGreaterEqual(target_va, info.segment_vaddr)
            self.assertLess(target_va, info.segment_vaddr + info.payload_size)
            target_file = _segment_file_offset(info, target_va)
            expected = encode_ps2_english(english, collapse_spaces=False) + b"\x00"
            self.assertEqual(expected, result[target_file:target_file + len(expected)])

        eof_va = struct.unpack_from("<I", result, table_file + len(HANT_WRAPPED_LINES) * 4)[0]
        self.assertEqual(0x795FBC, eof_va)

        metadata_va = struct.unpack_from("<I", result, HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET)[0]
        self.assertGreaterEqual(metadata_va, info.segment_vaddr)
        self.assertLess(metadata_va, info.segment_vaddr + info.payload_size)
        metadata_file = _segment_file_offset(info, metadata_va)
        actual_metadata = tuple(
            struct.unpack_from("<hhhh", result, metadata_file + index * 8)
            for index in range(len(HANT_CONTROLLER_METADATA_RECORDS))
        )
        self.assertEqual(HANT_CONTROLLER_METADATA_RECORDS, actual_metadata)

        # The pristine 17-entry tutorial table and icon metadata become immutable
        # provenance; only their proven leaf descriptors are redirected.
        self.assertEqual(
            RAW[HANT_POINTER_TABLE_OFFSET:HANT_POINTER_TABLE_OFFSET + 17 * 4],
            result[HANT_POINTER_TABLE_OFFSET:HANT_POINTER_TABLE_OFFSET + 17 * 4],
        )
        metadata_size = len(HANT_PRISTINE_CONTROLLER_METADATA_RECORDS) * 8
        self.assertEqual(
            RAW[HANT_CONTROLLER_METADATA_OFFSET:HANT_CONTROLLER_METADATA_OFFSET + metadata_size],
            result[HANT_CONTROLLER_METADATA_OFFSET:HANT_CONTROLLER_METADATA_OFFSET + metadata_size],
        )

    def test_relocates_hant_chrome_labels_through_proven_seven_entry_owner_table(self) -> None:
        import tools.hant_ui as hant_ui

        expected = (
            ("main_menu", 0x586CB0, 0x586D20, "【メインメニュー】", "【Main Menu】"),
            ("mail", 0x586CC8, 0x586D24, "【メール】", "【Mail】"),
            ("dictionary", 0x586CD8, 0x586D28, "【用語辞典】", "【Dictionary】"),
            ("enemy", 0x695888, 0x586D2C, "【敵】", "【Enemy】"),
            ("memo", 0x586CE8, 0x586D30, "【睡院メモ】", "【Memo】"),
            ("help", 0x586CF8, 0x586D34, "【ヘルプ】", "【Help】"),
            ("config", 0x586D08, 0x586D38, "【コンフィグ】", "【Config】"),
        )
        self.assertEqual(expected, tuple(
            (spec.key, spec.source_offset, spec.pointer_offset, spec.source_text, spec.english)
            for spec in hant_ui.HANT_CHROME_LABELS
        ))
        self.assertTrue(all(spec.provenance == "semantic" for spec in hant_ui.HANT_CHROME_LABELS))

        result, info = patch_hant_tutorial(RAW)
        for spec in hant_ui.HANT_CHROME_LABELS:
            with self.subTest(key=spec.key):
                # Relocation leaves the Japanese source as immutable provenance.
                source = spec.source_text.encode("cp932") + b"\x00"
                self.assertEqual(source, result[spec.source_offset:spec.source_offset + len(source)])

                target_va = struct.unpack_from("<I", result, spec.pointer_offset)[0]
                self.assertGreaterEqual(target_va, info.segment_vaddr)
                self.assertLess(target_va, info.segment_vaddr + info.payload_size)
                target_file = _segment_file_offset(info, target_va)
                translated = encode_ps2_english(spec.english, collapse_spaces=False) + b"\x00"
                self.assertEqual(translated, result[target_file:target_file + len(translated)])

        tampered = bytearray(RAW)
        tampered[0x586D20] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T chrome.*pointer"):
            patch_hant_tutorial(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[0x586CB0] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T chrome.*source"):
            patch_hant_tutorial(bytes(tampered))

    def test_relocates_visible_help_topic_list_to_semantic_english(self) -> None:
        topics = (
            (0x5876E0, 0x587840, "Ｈ．Ａ．Ｎ．Ｔの機能", "H.A.N.T Functions"),
            (0x587700, 0x587844, "コマンドサムネイル", "Command Thumbnails"),
            (0x587718, 0x587848, "自室について", "About Your Room"),
            (0x587730, 0x58784C, "ショッピングサイト", "Shopping Site"),
            (0x587748, 0x587850, "ギルドサイト", "Guild Site"),
            (0x587758, 0x587854, "売店について", "About the Shop"),
            (0x587770, 0x587858, "アイテム画面について", "Item Screen"),
            (0x587790, 0x58785C, "アイテムの使い方", "Using Items"),
            (0x5877A8, 0x587860, "アイテムの携行", "Carrying Items"),
            (0x5877B8, 0x587864, "アイテムの装備", "Equipping Items"),
            (0x5877D0, 0x587868, "リサイクルについて", "Recycling"),
            (0x5877E8, 0x58786C, "アイテムの調合", "Item Synthesis"),
            (0x5877F8, 0x587870, "弾薬について", "Ammunition"),
            (0x587810, 0x587874, "レベルアップしたら", "When You Level Up"),
            (0x587828, 0x587878, "セーブ＆ロード", "Save & Load"),
        )
        result, info = patch_hant_tutorial(RAW)

        for source_offset, pointer_offset, source_text, english in topics:
            with self.subTest(source=source_text):
                source = source_text.encode("cp932") + b"\x00"
                self.assertEqual(source, result[source_offset:source_offset + len(source)])
                target_va = struct.unpack_from("<I", result, pointer_offset)[0]
                self.assertGreaterEqual(target_va, info.segment_vaddr)
                self.assertLess(target_va, info.segment_vaddr + info.payload_size)
                target_file = _segment_file_offset(info, target_va)
                translated = encode_ps2_english(english, collapse_spaces=False) + b"\x00"
                self.assertEqual(translated, result[target_file:target_file + len(translated)])

    def test_help_descriptor_vector_proves_three_sibling_topic_tables(self) -> None:
        import tools.hant_ui as hant_ui

        self.assertEqual(0x587890, hant_ui.HANT_HELP_CATEGORY_DESCRIPTOR_OFFSET)
        self.assertEqual(
            (0x006873B0, 0x00687610, 0x006877C0),
            struct.unpack_from("<3I", RAW, hant_ui.HANT_HELP_CATEGORY_DESCRIPTOR_OFFSET),
        )
        self.assertEqual(20, len(hant_ui.HANT_ADV_HELP_TOPICS))
        self.assertEqual(20, len(hant_ui.HANT_EXPLORATION_HELP_TOPICS))
        self.assertEqual(15, len(hant_ui.HANT_HELP_TOPICS))
        self.assertTrue(all(spec.provenance == "semantic" for spec in hant_ui.HANT_ALL_HELP_TOPICS))

    def test_help_category_labels_are_owned_by_live_three_entry_renderer(self) -> None:
        import tools.hant_ui as hant_ui

        self.assertEqual(0x587288, hant_ui.HANT_HELP_CATEGORY_LABEL_TABLE_OFFSET)
        self.assertEqual(3, len(hant_ui.HANT_HELP_CATEGORY_LABELS))
        self.assertEqual(
            (0x3C030068, 0x24637208, 0x00711821, 0x8C650000, 0x0C062820, 0x2A620003),
            tuple(
                struct.unpack_from("<I", RAW, offset)[0]
                for offset in (0x18C818, 0x18C81C, 0x18C820, 0x18C828, 0x18C82C, 0x18C838)
            ),
        )
        self.assertEqual(
            ("ADV", "Ruins", "Other"),
            tuple(spec.english for spec in hant_ui.HANT_HELP_CATEGORY_LABELS),
        )
        self.assertTrue(all(spec.provenance == "semantic" for spec in hant_ui.HANT_HELP_CATEGORY_LABELS))

    def test_relocates_help_category_labels_to_semantic_english(self) -> None:
        import tools.hant_ui as hant_ui

        result, info = patch_hant_tutorial(RAW)
        for spec in hant_ui.HANT_HELP_CATEGORY_LABELS:
            with self.subTest(key=spec.key):
                source = spec.source_text.encode("cp932") + b"\x00"
                self.assertEqual(source, result[spec.source_offset:spec.source_offset + len(source)])
                target_va = struct.unpack_from("<I", result, spec.pointer_offset)[0]
                self.assertGreaterEqual(target_va, info.segment_vaddr)
                self.assertLess(target_va, info.segment_vaddr + info.payload_size)
                target_file = _segment_file_offset(info, target_va)
                translated = encode_ps2_english(spec.english, collapse_spaces=False) + b"\x00"
                self.assertEqual(translated, result[target_file:target_file + len(translated)])

        tampered = bytearray(RAW)
        tampered[0x18C81C] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T help category renderer"):
            patch_hant_tutorial(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[hant_ui.HANT_HELP_CATEGORY_LABELS[0].pointer_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T help-category.*pointer"):
            patch_hant_tutorial(bytes(tampered))

    def test_relocates_all_three_proven_help_topic_lists_to_semantic_english(self) -> None:
        import tools.hant_ui as hant_ui

        result, info = patch_hant_tutorial(RAW)
        self.assertEqual(55, len(hant_ui.HANT_ALL_HELP_TOPICS))

        for spec in hant_ui.HANT_ALL_HELP_TOPICS:
            with self.subTest(key=spec.key):
                source = spec.source_text.encode("cp932") + b"\x00"
                self.assertEqual(source, result[spec.source_offset:spec.source_offset + len(source)])
                target_va = struct.unpack_from("<I", result, spec.pointer_offset)[0]
                self.assertGreaterEqual(target_va, info.segment_vaddr)
                self.assertLess(target_va, info.segment_vaddr + info.payload_size)
                target_file = _segment_file_offset(info, target_va)
                translated = encode_ps2_english(spec.english, collapse_spaces=False) + b"\x00"
                self.assertEqual(translated, result[target_file:target_file + len(translated)])

        tampered = bytearray(RAW)
        tampered[hant_ui.HANT_HELP_CATEGORY_DESCRIPTOR_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T help category descriptor"):
            patch_hant_tutorial(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[hant_ui.HANT_ADV_HELP_TOPICS[0].pointer_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T help-topic.*pointer"):
            patch_hant_tutorial(bytes(tampered))

    def test_config_labels_are_owned_by_live_nine_entry_config_renderer(self) -> None:
        import tools.hant_ui as hant_ui

        self.assertEqual(0x586EF0, hant_ui.HANT_CONFIG_POINTER_TABLE_OFFSET)
        self.assertEqual(9, len(hant_ui.HANT_CONFIG_LABELS))
        self.assertEqual(
            (0x3C030068, 0x24636E70, 0x00711821, 0x8C650000, 0x0C062820, 0x2A420009),
            tuple(
                struct.unpack_from("<I", RAW, offset)[0]
                for offset in (0x18BCA4, 0x18BCA8, 0x18BCAC, 0x18BCB4, 0x18BCB8, 0x18BCC4)
            ),
        )
        self.assertTrue(all(spec.provenance == "semantic" for spec in hant_ui.HANT_CONFIG_LABELS))

    def test_relocates_proven_config_labels_to_semantic_english(self) -> None:
        import tools.hant_ui as hant_ui

        result, info = patch_hant_tutorial(RAW)
        expected = (
            "Voice/SFX Volume",
            "BGM Volume",
            "Emotion Speed",
            "Walk Camera",
            "Vibration",
            "Audio",
            "Message Icon",
            "Voice Nav",
            "Ringtone",
        )
        self.assertEqual(expected, tuple(spec.english for spec in hant_ui.HANT_CONFIG_LABELS))

        for spec in hant_ui.HANT_CONFIG_LABELS:
            with self.subTest(key=spec.key):
                source = spec.source_text.encode("cp932") + b"\x00"
                self.assertEqual(source, result[spec.source_offset:spec.source_offset + len(source)])
                target_va = struct.unpack_from("<I", result, spec.pointer_offset)[0]
                self.assertGreaterEqual(target_va, info.segment_vaddr)
                self.assertLess(target_va, info.segment_vaddr + info.payload_size)
                target_file = _segment_file_offset(info, target_va)
                translated = encode_ps2_english(spec.english, collapse_spaces=False) + b"\x00"
                self.assertEqual(translated, result[target_file:target_file + len(translated)])

        tampered = bytearray(RAW)
        tampered[0x18BCA8] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T config renderer"):
            patch_hant_tutorial(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[hant_ui.HANT_CONFIG_LABELS[0].pointer_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T config.*pointer"):
            patch_hant_tutorial(bytes(tampered))

    def test_tutorial_rows_use_existing_12px_font_style_without_global_font_patch(self) -> None:
        result, _info = patch_hant_tutorial(RAW)

        # VA 0x2908E8 is the mode-4 tutorial row constructor's font-style arg.
        # Pristine style 0 is 16x18; style 1 is the existing 12x12 record.
        self.assertEqual(0x0000282D, struct.unpack_from("<I", RAW, 0x190968)[0])
        self.assertEqual(0x24050001, struct.unpack_from("<I", result, 0x190968)[0])
        self.assertLessEqual(
            131 + (len(HANT_WRAPPED_LINES) - 1) * HANT_LAYOUT_PROFILE.line_spacing + 12,
            416,
        )

        tampered = bytearray(RAW)
        tampered[0x190968] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T.*style|H.A.N.T.*renderer"):
            patch_hant_tutorial(bytes(tampered))

    def test_tutorial_rows_use_page_local_16px_vertical_spacing(self) -> None:
        result, _info = patch_hant_tutorial(RAW)

        # VA 0x2907E4 materializes the page-local 21.0f row stride used by
        # ``131 + stride * row``. r6 runtime keeps the 12px font readable but
        # shows the page rows are still too loose. Tighten only this page-local
        # stride to 16.0f, leaving 4px leading around the 12px glyph height.
        self.assertEqual(16.0, HANT_LAYOUT_PROFILE.line_spacing)
        self.assertEqual(0x3C0241A8, struct.unpack_from("<I", RAW, 0x190864)[0])
        self.assertEqual(0x3C024180, struct.unpack_from("<I", result, 0x190864)[0])

    def test_wrapping_preserves_instructional_wording_and_uses_runtime_row_budget(self) -> None:
        # The standalone H.A.N.T heading is presentation-only and redundant with
        # both the page chrome and the first body sentence. The runtime-good pixel
        # span is ~336 px; style 1 renders 12 px glyphs, allowing 28 cells and 14
        # rows while preserving all instructional wording under the 16-row cap.
        expected = " ".join((
            *(HANT_ENGLISH_LINES[index].strip() for index in (2, 3, 4)),
            HANT_ENGLISH_LINES[7].strip(),
            *(HANT_ENGLISH_LINES[index].strip() for index in (9, 10, 12, 13, 14)),
        ))
        self.assertEqual(expected, " ".join(line for line in HANT_WRAPPED_LINES if line))

    def test_unresolved_hant_candidates_remain_pristine(self) -> None:
        result, _info = patch_hant_tutorial(RAW)
        from tools.hant_ui import HANT_HELP_TOPICS

        promoted_help_sources = {spec.source_offset for spec in HANT_HELP_TOPICS}
        candidates = [
            entry for entry in inventory_hant_text(RAW, None)
            if entry.owner == "executable_hant_candidate"
            and entry.source_offset not in promoted_help_sources
        ]
        self.assertGreaterEqual(len(candidates), 9)

        for entry in candidates:
            with self.subTest(key=entry.key):
                encoded = entry.source_text.encode("cp932") + b"\x00"
                self.assertEqual(
                    RAW[entry.source_offset:entry.source_offset + len(encoded)],
                    result[entry.source_offset:entry.source_offset + len(encoded)],
                )
                for pointer_offset in entry.pointer_offsets:
                    self.assertEqual(
                        RAW[pointer_offset:pointer_offset + 4],
                        result[pointer_offset:pointer_offset + 4],
                    )

    def test_fail_closes_if_hant_source_pointer_or_descriptor_is_not_pristine(self) -> None:
        tampered = bytearray(RAW)
        tampered[0x5C8B10] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T source"):
            patch_hant_tutorial(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[HANT_POINTER_TABLE_OFFSET + 3 * 4] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T pointer"):
            patch_hant_tutorial(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[HANT_TUTORIAL_DESCRIPTOR_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T tutorial descriptor"):
            patch_hant_tutorial(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[HANT_CONTROLLER_METADATA_OFFSET + 4] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T controller metadata"):
            patch_hant_tutorial(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T controller metadata descriptor"):
            patch_hant_tutorial(bytes(tampered))


if __name__ == "__main__":
    unittest.main()
