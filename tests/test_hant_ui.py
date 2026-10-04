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

        self.assertEqual(160849, info.payload_size)
        self.assertEqual(
            "c085742ab2e5b1d35168cf9ea0167bf674f18b970b48d0efb9ce63f1f7bf0ea6",
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

    def test_about_shop_help_body_owner_is_separate_from_topic_label_owner(self) -> None:
        import tools.hant_ui as hant_ui

        bodies = {body.key: body for body in getattr(hant_ui, "HANT_HELP_BODIES", ())}
        self.assertIn("shop", bodies)
        spec = bodies["shop"]
        self.assertEqual("shop", spec.key)
        self.assertEqual((4, 2, 5), (spec.mode, spec.category_index, spec.topic_index))
        self.assertEqual(0x5CBAC4, spec.descriptor_offset)
        self.assertEqual(0x5C9B80, spec.source_table_offset)
        self.assertEqual(0x5CBA74, spec.metadata_descriptor_offset)
        self.assertEqual(0x698968, spec.metadata_offset)
        self.assertEqual("semantic", spec.provenance)
        self.assertEqual(
            (
                "       About the Shop",
                "",
                "During lunch, visit the Shop",
                "You can buy food, supplies,",
                "and other useful items.",
                "",
                "",
            ),
            spec.english_rows,
        )
        self.assertTrue(all(measured_hant_cells(row) <= HANT_LAYOUT_PROFILE.max_cells for row in spec.english_rows))
        self.assertEqual(
            (0x006C9A60, 0x00795FB8, 0x006C9A80, 0x006C9AB0, 0x006C9AD0, 0x00795FB8, 0x00795FB8, 0x00795FBC),
            struct.unpack_from("<8I", RAW, spec.source_table_offset),
        )
        self.assertEqual(0x006C9B00, struct.unpack_from("<I", RAW, spec.descriptor_offset)[0])
        self.assertEqual((-1, -1, -1, -1), struct.unpack_from("<hhhh", RAW, spec.metadata_offset))
        self.assertEqual(0x007988E8, struct.unpack_from("<I", RAW, spec.metadata_descriptor_offset)[0])

    def test_relocates_about_shop_help_body_without_mutating_pristine_rows_or_metadata(self) -> None:
        import tools.hant_ui as hant_ui

        bodies = {body.key: body for body in getattr(hant_ui, "HANT_HELP_BODIES", ())}
        self.assertIn("shop", bodies)
        spec = bodies["shop"]
        result, info = patch_hant_tutorial(RAW)

        target_table_va = struct.unpack_from("<I", result, spec.descriptor_offset)[0]
        self.assertGreaterEqual(target_table_va, info.segment_vaddr)
        self.assertLess(target_table_va, info.segment_vaddr + info.payload_size)
        target_table_file = _segment_file_offset(info, target_table_va)

        for index, english in enumerate(spec.english_rows):
            target_va = struct.unpack_from("<I", result, target_table_file + index * 4)[0]
            if not english:
                self.assertEqual(0x00795FB8, target_va)
                continue
            self.assertGreaterEqual(target_va, info.segment_vaddr)
            self.assertLess(target_va, info.segment_vaddr + info.payload_size)
            target_file = _segment_file_offset(info, target_va)
            encoded = encode_ps2_english(english, collapse_spaces=False) + b"\x00"
            self.assertEqual(encoded, result[target_file:target_file + len(encoded)])

        self.assertEqual(0x00795FBC, struct.unpack_from("<I", result, target_table_file + len(spec.english_rows) * 4)[0])
        self.assertEqual(
            RAW[spec.source_table_offset:spec.source_table_offset + 8 * 4],
            result[spec.source_table_offset:spec.source_table_offset + 8 * 4],
        )
        self.assertEqual(
            RAW[spec.metadata_offset:spec.metadata_offset + 8],
            result[spec.metadata_offset:spec.metadata_offset + 8],
        )
        self.assertEqual(
            RAW[spec.metadata_descriptor_offset:spec.metadata_descriptor_offset + 4],
            result[spec.metadata_descriptor_offset:spec.metadata_descriptor_offset + 4],
        )

        tampered = bytearray(RAW)
        tampered[spec.descriptor_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T help-body.*descriptor"):
            patch_hant_tutorial(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[spec.source_table_offset + 2 * 4] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T help-body.*table"):
            patch_hant_tutorial(bytes(tampered))

    def test_runtime_reported_help_bodies_are_promoted_as_separate_owners(self) -> None:
        import tools.hant_ui as hant_ui

        bodies = {spec.key: spec for spec in getattr(hant_ui, "HANT_HELP_BODIES", ())}
        self.assertEqual(
            {"adv_controls", "exploration_controls", "moving_in_ruins", "shop"},
            set(bodies),
        )
        expected = {
            "adv_controls": ((4, 0, 0), 0x5C4390, 0x5C2E30, 0x5C4340, 0x5C2C70, 8),
            "exploration_controls": ((4, 1, 0), 0x5C8A50, 0x5C4650, 0x5C8A00, 0x5C43E0, 14),
            "moving_in_ruins": ((4, 1, 1), 0x5C8A54, 0x5C4B20, 0x5C8A04, 0x5C46A0, 34),
            "shop": ((4, 2, 5), 0x5CBAC4, 0x5C9B80, 0x5CBA74, 0x698968, 0),
        }
        for key, (indices, descriptor, table, metadata_descriptor, metadata, metadata_count) in expected.items():
            with self.subTest(key=key):
                spec = bodies[key]
                self.assertEqual(indices, (spec.mode, spec.category_index, spec.topic_index))
                self.assertEqual(descriptor, spec.descriptor_offset)
                self.assertEqual(table, spec.source_table_offset)
                self.assertEqual(metadata_descriptor, spec.metadata_descriptor_offset)
                self.assertEqual(metadata, spec.metadata_offset)
                self.assertEqual(metadata_count, len(spec.metadata_records))
                self.assertEqual("semantic", spec.provenance)
                self.assertTrue(all(measured_hant_cells(row) <= HANT_LAYOUT_PROFILE.max_cells for row in spec.english_rows))

    def test_runtime_reported_help_body_metadata_moves_with_english_geometry(self) -> None:
        import tools.hant_ui as hant_ui

        result, info = patch_hant_tutorial(RAW)
        expected_edges = {
            "adv_controls": ((38, 0, 4, 5), (0, 4, 23, 156)),
            "exploration_controls": ((38, 0, 4, 5), (38, 10, 4, 225)),
            "moving_in_ruins": ((29, 0, 10, 89), (0, 6, 10, 622)),
        }
        for spec in hant_ui.HANT_HELP_BODIES:
            with self.subTest(key=spec.key):
                metadata_size = (len(spec.metadata_records) + 1) * 8
                # Japanese metadata remains immutable provenance.
                self.assertEqual(
                    RAW[spec.metadata_offset:spec.metadata_offset + metadata_size],
                    result[spec.metadata_offset:spec.metadata_offset + metadata_size],
                )
                target_table_va = struct.unpack_from("<I", result, spec.descriptor_offset)[0]
                self.assertGreaterEqual(target_table_va, info.segment_vaddr)
                self.assertLess(target_table_va, info.segment_vaddr + info.payload_size)

                metadata_va = struct.unpack_from("<I", result, spec.metadata_descriptor_offset)[0]
                if not spec.metadata_records:
                    self.assertEqual(struct.unpack_from("<I", RAW, spec.metadata_descriptor_offset)[0], metadata_va)
                    continue
                self.assertGreaterEqual(metadata_va, info.segment_vaddr)
                self.assertLess(metadata_va, info.segment_vaddr + info.payload_size)
                metadata_file = _segment_file_offset(info, metadata_va)
                records = tuple(
                    struct.unpack_from("<hhhh", result, metadata_file + index * 8)
                    for index in range(len(spec.metadata_records) + 1)
                )
                self.assertEqual((-1, -1, -1, -1), records[-1])
                self.assertEqual(expected_edges[spec.key][0], records[0])
                self.assertEqual(expected_edges[spec.key][1], records[-2])

    def test_r14_runtime_layout_defects_use_english_font_and_spacing_owners(self) -> None:
        import tools.hant_ui as hant_ui

        result, _info = patch_hant_tutorial(RAW)
        # Config labels and selected values use the same existing 12px style 1 as
        # the runtime-good English H.A.N.T tutorial instead of Japanese style 0.
        for offset in (0x18BC84, 0x18BF14):
            self.assertEqual(0x0000282D, struct.unpack_from("<I", RAW, offset)[0])
            self.assertEqual(0x24050001, struct.unpack_from("<I", result, offset)[0])
        # Dictionary term rows and top index tabs likewise switch to style 1.
        for offset in (0x18E2CC, 0x18E408):
            self.assertEqual(0x0000282D, struct.unpack_from("<I", RAW, offset)[0])
            self.assertEqual(0x24050001, struct.unpack_from("<I", result, offset)[0])
        # 0x190968 is the proven mode-4 H.A.N.T body-row font owner and remains
        # style 1. r14 runtime disproves 0x190A40 as a Dictionary-detail style
        # owner: changing that singleton constructor blanks H.A.N.T Functions and
        # leaves the H.A.N.T state trapped, so it must remain pristine style 0.
        self.assertEqual(0x0000282D, struct.unpack_from("<I", RAW, 0x190968)[0])
        self.assertEqual(0x24050001, struct.unpack_from("<I", result, 0x190968)[0])
        self.assertEqual(0x0000282D, struct.unpack_from("<I", RAW, 0x190A40)[0])
        self.assertEqual(0x0000282D, struct.unpack_from("<I", result, 0x190A40)[0])
        # r18 runtime proves that moving only the Dictionary tabs cannot produce a
        # coherent header: the 192px English chrome already overlaps pristine L1.
        # r19 owns the complete root-nav row instead. Keep the 12px tab glyphs,
        # pack them at 12px cadence, and place the cluster after the title: title
        # ends at x=267, L1 starts at 274, tabs span 302..422, and R1 starts at 428.
        self.assertEqual(0x3C024343, struct.unpack_from("<I", RAW, 0x18E1A4)[0])
        self.assertEqual(0x3C024389, struct.unpack_from("<I", result, 0x18E1A4)[0])
        self.assertEqual(0x24020197, struct.unpack_from("<I", RAW, 0x18E1EC)[0])
        self.assertEqual(0x240201AC, struct.unpack_from("<I", result, 0x18E1EC)[0])
        self.assertEqual(0x3C024190, struct.unpack_from("<I", RAW, 0x18E398)[0])
        self.assertEqual(0x3C024140, struct.unpack_from("<I", result, 0x18E398)[0])
        self.assertEqual(0x3C024361, struct.unpack_from("<I", RAW, 0x18E3AC)[0])
        self.assertEqual(0x3C024397, struct.unpack_from("<I", result, 0x18E3AC)[0])
        # Dictionary detail title/icon X derives only from the mode-offset table.
        # Japanese 【用語辞典】 is six 16px glyphs; English 【Dictionary】 is twelve.
        # Mode 1 therefore needs six extra 16px cells, not r17's two. Offset 12
        # puts the icon/title beyond the translated chrome without touching the
        # generic constructor or the r15-critical 0x190A40 singleton.
        self.assertEqual(6, struct.unpack_from("<I", RAW, 0x588C84)[0])
        self.assertEqual(12, struct.unpack_from("<I", result, 0x588C84)[0])
        # Enemy uses the same header pattern. r21 keeps y=93/style 1 and packs
        # category starts to 220/282/344 so Human clears runtime-good R1 x=407.
        self.assertEqual(0x3C024382, struct.unpack_from("<I", RAW, 0x195BCC)[0])
        self.assertEqual(0x3C024342, struct.unpack_from("<I", result, 0x195BCC)[0])
        self.assertEqual(0x24020197, struct.unpack_from("<I", RAW, 0x195C14)[0])
        # r19 runtime shows x=428 clips R1. Keep the original proven x=407.
        self.assertEqual(0x24020197, struct.unpack_from("<I", result, 0x195C14)[0])
        self.assertEqual((0x2402010F, 0x24020137, 0x2402015F), tuple(struct.unpack_from("<I", RAW, o)[0] for o in (0x195CB4, 0x195CD0, 0x195CEC)))
        self.assertEqual((0x240200C7, 0x24020105, 0x24020143), tuple(struct.unpack_from("<I", result, o)[0] for o in (0x195CB4, 0x195CD0, 0x195CEC)))
        self.assertEqual(0x3C0242BA, struct.unpack_from("<I", RAW, 0x195D18)[0])
        self.assertEqual(0x3C0242BA, struct.unpack_from("<I", result, 0x195D18)[0])
        self.assertEqual(0x0000282D, struct.unpack_from("<I", RAW, 0x195D5C)[0])
        self.assertEqual(0x24050001, struct.unpack_from("<I", result, 0x195D5C)[0])

        # Empty Mail is assigned to row 4 after construction, so its live X owner
        # is the shared Mail-row constructor. English style-0 text is 17*16=272px;
        # x=120 centers it in the 512px H.A.N.T. viewport.
        self.assertEqual(0x3C02430F, struct.unpack_from("<I", RAW, 0x193564)[0])
        self.assertEqual(0x3C0242F0, struct.unpack_from("<I", result, 0x193564)[0])

        by_key = {spec.key: spec for spec in hant_ui.HANT_CONTENT_LABELS}
        self.assertEqual("No mail received.", by_key["mail_empty"].english)
        self.assertEqual("     No data.", by_key["dictionary_empty"].english)
        self.assertEqual("No data.", by_key["enemy_empty"].english)
        # Keep the two source count cells so the separately rendered unread
        # number has a reserved gap instead of colliding with the English text.
        self.assertEqual("msgs  new", hant_ui.HANT_MAIL_COUNT_LABEL.english)

    def test_r20_dictionary_selector_tracks_repacked_english_tabs(self) -> None:
        result, _info = patch_hant_tutorial(RAW)
        # The moving selector is a separate owner from the ten text canvases.
        # Pristine uses selector x = 223 + 18*category while text is
        # x = 225 + 18*category. r19 moved only text to 302 + 12*category.
        # Preserve the original 2px inset with selector x = 300 + 12*category.
        self.assertEqual(0x3C03435F, struct.unpack_from("<I", RAW, 0x18DFD8)[0])
        self.assertEqual(0x3C034396, struct.unpack_from("<I", result, 0x18DFD8)[0])
        self.assertEqual(0x3C034190, struct.unpack_from("<I", RAW, 0x18F7B4)[0])
        self.assertEqual(0x3C034140, struct.unpack_from("<I", result, 0x18F7B4)[0])
        # Detail-page clearance and the H.A.N.T Functions singleton stay frozen.
        self.assertEqual(12, struct.unpack_from("<I", result, 0x588C84)[0])
        self.assertEqual(0x0000282D, struct.unpack_from("<I", result, 0x190A40)[0])

    def test_r21_enemy_selector_tracks_compact_english_categories(self) -> None:
        result, _info = patch_hant_tutorial(RAW)
        # Pristine selection box follows x = 288 + 40*category, four pixels
        # before Japanese category text. r21 preserves that inset while packing
        # the English row to selector x = 216 + 62*category.
        self.assertEqual(0x3C024220, struct.unpack_from("<I", RAW, 0x195F28)[0])
        self.assertEqual(0x3C024278, struct.unpack_from("<I", result, 0x195F28)[0])
        self.assertEqual(0x3C024390, struct.unpack_from("<I", RAW, 0x195F30)[0])
        self.assertEqual(0x3C02435A, struct.unpack_from("<I", result, 0x195F30)[0])
        self.assertEqual((0x240200C7, 0x24020105, 0x24020143), tuple(
            struct.unpack_from("<I", result, o)[0]
            for o in (0x195CB4, 0x195CD0, 0x195CEC)
        ))

    def test_r21_selector_resources_have_bounded_intrinsic_width_owners(self) -> None:
        result, _info = patch_hant_tutorial(RAW)

        # Both red selectors are unique group-20 sprite resources. Keep their
        # resource-table ownership fail-closed before changing only rendered width.
        self.assertEqual(0x00482E50, struct.unpack_from("<I", RAW, 0x385310)[0])
        self.assertEqual((0x00464B30, 1), struct.unpack_from("<II", RAW, 0x382FD8))
        self.assertEqual((0x00465730, 1), struct.unpack_from("<II", RAW, 0x3830D8))

        # Dictionary index 0x21 is intrinsically 24px wide, which spans two
        # 12px English tabs in r20. r21 stretches the same texture to 14px; its
        # UV rectangle remains byte-identical so no neighboring atlas art leaks.
        self.assertEqual(24.0, struct.unpack_from("<f", RAW, 0x364BB4)[0])
        self.assertEqual(16.0, struct.unpack_from("<f", result, 0x364BB4)[0])
        self.assertEqual(RAW[0x364BB8:0x364BD0], result[0x364BB8:0x364BD0])

        # Enemy index 0x41 is only 40px wide, shorter than a 5-glyph style-1
        # English category (60px). Stretch to 64px while preserving its UVs.
        self.assertEqual(40.0, struct.unpack_from("<f", RAW, 0x3657B4)[0])
        self.assertEqual(64.0, struct.unpack_from("<f", result, 0x3657B4)[0])
        self.assertEqual(RAW[0x3657B8:0x3657D0], result[0x3657B8:0x3657D0])

    def test_r21_enemy_header_clears_r1_without_shrinking_text(self) -> None:
        result, _info = patch_hant_tutorial(RAW)

        # Keep style 1 (12px). Pack the three 60px words at 220/282/344,
        # leaving Human ending at x=404 before the runtime-good R1 at x=407.
        self.assertEqual(0x24050001, struct.unpack_from("<I", result, 0x195D5C)[0])
        self.assertEqual(
            (0x240200C7, 0x24020105, 0x24020143),
            tuple(struct.unpack_from("<I", result, o)[0] for o in (0x195CB4, 0x195CD0, 0x195CEC)),
        )
        # Selector retains its proven four-pixel leading inset and follows the
        # same 62px cadence: x=216/278/340, with 64px rendered width.
        self.assertEqual(0x3C024278, struct.unpack_from("<I", result, 0x195F28)[0])
        self.assertEqual(0x3C02435A, struct.unpack_from("<I", result, 0x195F30)[0])
        self.assertEqual(0x24020197, struct.unpack_from("<I", result, 0x195C14)[0])

    def test_r22_selectors_have_symmetric_padding_without_touching_labels(self) -> None:
        result, _info = patch_hant_tutorial(RAW)

        # Dictionary tabs remain 12px glyphs at x=302+12*i. A 16px box at
        # x=300+12*i gives 2px padding on both sides; the final box ends at
        # x=424, leaving four pixels before Dictionary R1 at x=428.
        self.assertEqual(16.0, struct.unpack_from("<f", result, 0x364BB4)[0])
        self.assertEqual(0x3C034396, struct.unpack_from("<I", result, 0x18DFD8)[0])
        self.assertEqual(0x3C034140, struct.unpack_from("<I", result, 0x18F7B4)[0])

        # Enemy labels stay at 220/282/344 and remain 60px wide. Shift only
        # the 64px selector base from x=216 to x=218, yielding symmetric 2px
        # padding. Human's box ends at x=406, before runtime-good R1 x=407.
        self.assertEqual(0x3C02435A, struct.unpack_from("<I", result, 0x195F30)[0])
        self.assertEqual(0x3C024278, struct.unpack_from("<I", result, 0x195F28)[0])
        self.assertEqual(64.0, struct.unpack_from("<f", result, 0x3657B4)[0])
        self.assertEqual(
            (0x240200C7, 0x24020105, 0x24020143),
            tuple(struct.unpack_from("<I", result, o)[0] for o in (0x195CB4, 0x195CD0, 0x195CEC)),
        )
        self.assertEqual(0x24020197, struct.unpack_from("<I", result, 0x195C14)[0])


    def test_exploration_warning_text_preserves_two_cell_icon_gutter(self) -> None:
        import tools.hant_ui as hant_ui

        spec = next(spec for spec in hant_ui.HANT_HELP_BODIES if spec.key == "exploration_controls")
        warning_rows = spec.english_rows[13:16]
        self.assertEqual((
            "  Night vision uses battery.",
            "  It drains while active.",
            "  At zero, it shuts off.",
        ), warning_rows)
        self.assertTrue(all(row.startswith("  ") for row in warning_rows))
        self.assertTrue(all(measured_hant_cells(row) <= HANT_LAYOUT_PROFILE.max_cells for row in warning_rows))

    def test_all_dictionary_definition_pages_are_promoted_fail_closed(self) -> None:
        import tools.hant_ui as hant_ui
        from tools.hant_content_data import HANT_DICTIONARY_TERM_DATA
        from tools.hant_dictionary_definitions import DICTIONARY_DEFINITION_MAX_CELLS, definition_source_fingerprint

        definitions = {spec.key: spec for spec in getattr(hant_ui, "HANT_DICTIONARY_DEFINITIONS", ())}
        expected_keys = {row[0] for row in HANT_DICTIONARY_TERM_DATA}
        self.assertEqual(208, len(definitions))
        self.assertEqual(expected_keys, set(definitions))
        expected = {
            "dict_a_00": (0x5AB380, 0x5A43B0, 15),
            "dict_k_02": (0x5AEA98, 0x5ABA20, 14),
            "dict_h_20": (0x5B9780, 0x5B87A0, 9),
        }
        result, info = patch_hant_tutorial(RAW)
        for key, spec in definitions.items():
            with self.subTest(key=key):
                self.assertEqual("official_exact_reflow", spec.provenance)
                self.assertGreater(spec.source_row_count, 0)
                self.assertEqual(64, len(spec.source_sha256))
                self.assertEqual(
                    spec.source_sha256,
                    definition_source_fingerprint(RAW, spec.source_table_offset, spec.source_row_count),
                )
                self.assertTrue(spec.english_rows)
                self.assertTrue(all(measured_hant_cells(row) <= DICTIONARY_DEFINITION_MAX_CELLS for row in spec.english_rows))
                source_size = (spec.source_row_count + 1) * 4
                self.assertEqual(RAW[spec.source_table_offset:spec.source_table_offset + source_size], result[spec.source_table_offset:spec.source_table_offset + source_size])
                table_va = struct.unpack_from("<I", result, spec.descriptor_offset)[0]
                self.assertGreaterEqual(table_va, info.segment_vaddr)
                self.assertLess(table_va, info.segment_vaddr + info.payload_size)
                table_file = _segment_file_offset(info, table_va)
                self.assertEqual(0x00795FBC, struct.unpack_from("<I", result, table_file + len(spec.english_rows) * 4)[0])

        for key, triple in expected.items():
            spec = definitions[key]
            self.assertEqual(triple, (spec.descriptor_offset, spec.source_table_offset, spec.source_row_count))

        tampered = bytearray(RAW)
        tampered[definitions["dict_a_00"].descriptor_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "Dictionary definition.*descriptor"):
            patch_hant_tutorial(bytes(tampered))

    def test_runtime_reported_hant_content_owner_manifest(self) -> None:
        import tools.hant_ui as hant_ui

        values = getattr(hant_ui, "HANT_CONTENT_LABELS", ())
        by_key = {spec.key: spec for spec in values}
        self.assertEqual({"config_stereo", "config_mono", "config_japanese", "config_english", "mail_empty", "dictionary_empty", "enemy_empty", "enemy_small", "enemy_large", "enemy_human"}, set(by_key))
        expected = {
            "config_stereo": (0x586F48, (0x6958C8,), "ステレオ", "Stereo"),
            "config_mono": (0x586F58, (0x6958CC,), "モノラル", "Mono"),
            "config_japanese": (0x6958D0, (0x6958E0,), "日本語", "Japanese"),
            "config_english": (0x6958D8, (0x6958E4,), "英語", "English"),
            "mail_empty": (0x589960, (0x695BD8,), "受信メールがありません。", "No mail received."),
            "dictionary_empty": (0x5878F0, (0x695968,), "データがありません。", "     No data."),
            "enemy_empty": (0x587260, (0x695900,), "データがありません。", "No data."),
            "enemy_small": (0x695BE8, (0x5899F8,), "小型", "Small"),
            "enemy_large": (0x695BF0, (0x5899FC,), "大型", "Large"),
            "enemy_human": (0x695BF8, (0x589A00,), "人物", "Human"),
        }
        for key, row in expected.items():
            with self.subTest(key=key):
                spec = by_key[key]
                self.assertEqual(row, (spec.source_offset, spec.pointer_offsets, spec.source_text, spec.english))
                self.assertEqual("semantic", spec.provenance)

    def test_dictionary_tabs_and_real_terms_have_semantic_english_owners(self) -> None:
        import tools.hant_ui as hant_ui

        tabs = getattr(hant_ui, "HANT_DICTIONARY_TABS", ())
        self.assertEqual(10, len(tabs))
        self.assertEqual(tuple("AKSTNHMYRW"), tuple(spec.english for spec in tabs))
        self.assertEqual(tuple(range(0x5878C0, 0x5878E8, 4)), tuple(spec.pointer_offsets[0] for spec in tabs))

        terms = getattr(hant_ui, "HANT_DICTIONARY_TERMS", ())
        self.assertEqual(208, len(terms))
        self.assertEqual(208, len({spec.pointer_offsets[0] for spec in terms}))
        self.assertTrue(all(spec.provenance == "semantic" for spec in terms))

        ringtones = getattr(hant_ui, "HANT_RINGTONES", ())
        self.assertEqual(20, len(ringtones))
        self.assertEqual(20, len({spec.pointer_offsets[0] for spec in ringtones}))
        self.assertTrue(all(len(spec.english) <= 14 for spec in ringtones))

        by_source = {spec.source_offset: spec for spec in terms}
        for source_offset, en in (
            (0x587910, "King Akhenaten"),
            (0x587958, "Anubis"),
            (0x587978, "Amaterasu"),
            (0x5884B8, "Heracleion"),
            (0x588A90, "Rosetta Stone"),
            (0x588B90, "Watatsumi"),
        ):
            self.assertIn(source_offset, by_source)
            self.assertEqual(en, by_source[source_offset].english)
            self.assertEqual("semantic", by_source[source_offset].provenance)

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

        import tools.hant_ui as hant_ui
        promoted_sources = {spec.source_offset for spec in HANT_HELP_TOPICS}
        promoted_sources.update(spec.source_offset for spec in hant_ui.HANT_DICTIONARY_TERMS)
        promoted_sources.update(spec.source_offset for spec in hant_ui.HANT_RINGTONES)
        promoted_sources.update(spec.source_offset for spec in hant_ui.HANT_CONTENT_LABELS)
        candidates = [
            entry for entry in inventory_hant_text(RAW, None)
            if entry.owner == "executable_hant_candidate"
            and entry.source_offset not in promoted_sources
        ]
        self.assertGreaterEqual(len(candidates), 8)

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
