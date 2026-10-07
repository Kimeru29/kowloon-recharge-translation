from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tools.adv_layout import ADV_DG_LAYOUT_PATCHES, ADV_SPEAKER_LAYOUT_PATCHES
from tools.companion_hud import (
    COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
    COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
    COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
    COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_HEIGHT_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_X_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_Y_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_WIDTH_OFFSET,
    COMPANION_ACTION_LABELS,
    COMPANION_ACTION_LAYOUT_PATCHES,
    COMPANION_ACTION_RUNTIME_PATCH_OFFSETS,
    COMPANION_COMMENT_LINES,
)
from tools.early_ui import EARLY_UI_PATCHES, build_early_ui_elf
from tools.dungeon_ui import DUNGEON_ACTION_LABELS, DUNGEON_ITEM_NAMES
from tools.menu_ui import MENU_LABELS
from tools.hant_inventory import inventory_hant_text
from tools.startup_ui import (
    NAME_BLANK_STRING_OFFSET,
    NAME_CONFIRMATION_FOCUS_PATCHES,
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
    HANT_ALL_HELP_TOPICS,
    HANT_CHROME_LABELS,
    HANT_CONFIG_LABELS,
    HANT_CONTENT_LABELS,
    HANT_DICTIONARY_DEFINITIONS,
    HANT_DICTIONARY_TABS,
    HANT_DICTIONARY_TERMS,
    HANT_HELP_BODIES,
    HANT_MAIL_COUNT_LABEL,
    HANT_RUNTIME_LAYOUT_PATCHES,
    HANT_RINGTONES,
    HANT_HELP_CATEGORY_LABELS,
    HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET,
    HANT_CONTROLLER_METADATA_RECORDS,
    HANT_POINTER_TABLE_OFFSET,
    HANT_TUTORIAL_DESCRIPTOR_OFFSET,
    HANT_TUTORIAL_FONT_STYLE_OFFSET,
    HANT_TUTORIAL_ROW_SPACING_OFFSET,
    HANT_WRAPPED_LINES,
)
from tools.memory_card_ui import (
    MEMORY_CARD_MESSAGES,
    MEMORY_CARD_POINTER_ALIASES,
    MEMORY_CARD_POINTER_TABLE_OFFSET,
)
from tools.elf_translation_segment import TRANSLATION_SEGMENT_VADDR
from tools.localization import encode_ps2_english
from tools.title_layout import TITLE_LABEL_BACKING_PATCHES
from tests.local_fixtures import require_local_fixture


ELF_PATH = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF_PATH.read_bytes()


class EarlyUiPatchTests(unittest.TestCase):
    def test_manifest_uses_wide_relocated_command_menu_localization(self) -> None:
        actual = {(patch.offset, patch.expected): patch.text for patch in EARLY_UI_PATCHES}
        by_offset = {spec.source_offset: spec for spec in MENU_LABELS}

        # Exact title labels are pointer-relocated and tested in test_startup_ui.
        self.assertNotIn((0x5CBDE8, "初めから"), actual)
        self.assertNotIn((0x5CBDF8, "続きから"), actual)
        expected = {
            0x3BC7C8: "Items", 0x3BC7D8: "Quests", 0x3BC7E8: "H.A.N.T",
            0x3BC7F8: "Save & load", 0x3BC808: "Leave room", 0x3BC818: "Shop",
            0x3BC828: "Guild site", 0x3BC838: "Broadband", 0x3BC848: "Collection",
            0x3BC868: "Next chapter", 0x3BC878: "End turn", 0x3BC888: "Return above ground",
            0x3BC898: "Interior", 0x694180: "None", 0x694188: "Map",
            0x694190: "Report card", 0x694198: "Noise", 0x6941A0: "Battle",
        }
        for offset, english in expected.items():
            with self.subTest(offset=hex(offset)):
                spec = by_offset[offset]
                self.assertEqual(english, spec.selected_english)
                self.assertEqual("relocated", spec.storage)
                self.assertEqual("proven", spec.status)
                self.assertNotIn((offset, spec.source_text), actual)
        self.assertEqual("unresolved", by_offset[0x3BC858].status)
        self.assertEqual("pristine", by_offset[0x3BC858].storage)

    def test_build_changes_only_declared_pristine_regions_before_appended_segment(self) -> None:
        result = build_early_ui_elf(RAW)

        allowed = set(range(TITLE_ARENA_START, TITLE_ARENA_END))
        allowed.update(range(TITLE_LOAD_POINTER_OFFSET, TITLE_LOAD_POINTER_OFFSET + 4))
        allowed.update(range(0x1ABF64, 0x1ABF68))
        allowed.update(range(0x1ABF84, 0x1ABF88))
        for off, _expected, _replacement in TITLE_LABEL_BACKING_PATCHES:
            allowed.update(range(off, off + 4))
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
        for off, _expected, _replacement in (*ADV_DG_LAYOUT_PATCHES, *ADV_SPEAKER_LAYOUT_PATCHES):
            allowed.update(range(off, off + 4))
        allowed.update(range(HANT_TUTORIAL_DESCRIPTOR_OFFSET, HANT_TUTORIAL_DESCRIPTOR_OFFSET + 4))
        for spec in HANT_HELP_BODIES:
            allowed.update(range(spec.descriptor_offset, spec.descriptor_offset + 4))
            if spec.metadata_records:
                allowed.update(range(spec.metadata_descriptor_offset, spec.metadata_descriptor_offset + 4))
        for spec in HANT_DICTIONARY_DEFINITIONS:
            allowed.update(range(spec.descriptor_offset, spec.descriptor_offset + 4))
        for off, _expected, _replacement in HANT_RUNTIME_LAYOUT_PATCHES:
            allowed.update(range(off, off + 4))
        allowed.update(range(HANT_MAIL_COUNT_LABEL.lui_offset, HANT_MAIL_COUNT_LABEL.lui_offset + 4))
        allowed.update(range(HANT_MAIL_COUNT_LABEL.addiu_offset, HANT_MAIL_COUNT_LABEL.addiu_offset + 4))
        allowed.update(
            range(HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET, HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET + 4)
        )
        allowed.update(range(HANT_TUTORIAL_FONT_STYLE_OFFSET, HANT_TUTORIAL_FONT_STYLE_OFFSET + 4))
        allowed.update(range(HANT_TUTORIAL_ROW_SPACING_OFFSET, HANT_TUTORIAL_ROW_SPACING_OFFSET + 4))
        for spec in (
            *HANT_CHROME_LABELS,
            *HANT_CONFIG_LABELS,
            *HANT_HELP_CATEGORY_LABELS,
            *HANT_ALL_HELP_TOPICS,
        ):
            allowed.update(range(spec.pointer_offset, spec.pointer_offset + 4))
        for spec in (*HANT_CONTENT_LABELS, *HANT_RINGTONES, *HANT_DICTIONARY_TABS, *HANT_DICTIONARY_TERMS):
            for pointer_offset in spec.pointer_offsets:
                allowed.update(range(pointer_offset, pointer_offset + 4))
        for offset in (0x181888, 0x1819DC, 0x181A68, 0x181AF4, 0x181B70, 0x181EAC):
            allowed.update(range(offset, offset + 4))
        for offset, _expected, _replacement in NAME_CONFIRMATION_FOCUS_PATCHES:
            allowed.update(range(offset, offset + 4))
        for index in MEMORY_CARD_MESSAGES:
            off = MEMORY_CARD_POINTER_TABLE_OFFSET + index * 4
            allowed.update(range(off, off + 4))
        for offsets in MEMORY_CARD_POINTER_ALIASES.values():
            for off in offsets:
                allowed.update(range(off, off + 4))
        for spec in MENU_LABELS:
            if spec.storage == "relocated":
                for off in spec.pointer_offsets:
                    allowed.update(range(off, off + 4))
        for spec in DUNGEON_ACTION_LABELS:
            allowed.update(range(spec.code_reference.lui_offset, spec.code_reference.lui_offset + 4))
            allowed.update(range(spec.code_reference.addiu_offset, spec.code_reference.addiu_offset + 4))
        for spec in DUNGEON_ITEM_NAMES:
            allowed.update(range(spec.pointer_offset, spec.pointer_offset + 4))
        for spec in COMPANION_COMMENT_LINES:
            for pointer_offset in spec.pointer_offsets:
                allowed.update(range(pointer_offset, pointer_offset + 4))
        for spec in COMPANION_ACTION_LABELS:
            if spec.english is not None:
                allowed.update(range(spec.pointer_offset, spec.pointer_offset + 4))
        for offset, _expected, _replacement in COMPANION_ACTION_LAYOUT_PATCHES:
            allowed.update(range(offset, offset + 4))
        for offset in COMPANION_ACTION_RUNTIME_PATCH_OFFSETS:
            allowed.update(range(offset, offset + 4))
        for offset in (
            COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
            COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
            COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
            COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
            COMPANION_ACTION_SLOT2_BUBBLE_WIDTH_OFFSET,
            COMPANION_ACTION_SLOT2_BUBBLE_HEIGHT_OFFSET,
            COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_X_OFFSET,
            COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_Y_OFFSET,
        ):
            allowed.update(range(offset, offset + 4))
        allowed.update(range(NAME_FLOW_STATE9_FLAG_OFFSET, NAME_FLOW_STATE9_FLAG_OFFSET + 4))
        # ELF program header / heap metadata used by the appended translation segment.
        allowed.update(range(0x54, 0x54 + 32))
        allowed.update(range(0x250, 0x254))
        allowed.update(range(0x650014, 0x650018))
        allowed.update(range(0x8030BC, 0x8030C0))

        differences = {index for index, (before, after) in enumerate(zip(RAW, result[:len(RAW)])) if before != after}
        self.assertTrue(differences)
        self.assertTrue(differences <= allowed)

    def test_unresolved_menu_sources_and_aliases_match_pristine_fixture(self) -> None:
        result = build_early_ui_elf(RAW)

        unresolved = [spec for spec in MENU_LABELS if spec.storage == "pristine"]
        self.assertTrue(unresolved)
        for spec in unresolved:
            with self.subTest(key=spec.key):
                self.assertEqual(
                    RAW[spec.source_offset:spec.source_offset + spec.capacity],
                    result[spec.source_offset:spec.source_offset + spec.capacity],
                )
                for pointer_offset in spec.pointer_offsets:
                    self.assertEqual(
                        RAW[pointer_offset:pointer_offset + 4],
                        result[pointer_offset:pointer_offset + 4],
                    )

    def test_unresolved_hant_candidates_match_pristine_fixture_except_cross_owned_sources(self) -> None:
        result = build_early_ui_elf(RAW)
        entries = inventory_hant_text(RAW, None)
        promoted_hant_sources = {spec.source_offset for spec in HANT_ALL_HELP_TOPICS}
        promoted_hant_sources.update(spec.source_offset for spec in HANT_CONTENT_LABELS)
        promoted_hant_sources.update(spec.source_offset for spec in HANT_RINGTONES)
        promoted_hant_sources.update(spec.source_offset for spec in HANT_DICTIONARY_TABS)
        promoted_hant_sources.update(spec.source_offset for spec in HANT_DICTIONARY_TERMS)
        candidates = [
            entry for entry in entries
            if entry.owner == "executable_hant_candidate"
            and entry.classification == "unresolved"
            and entry.source_offset not in promoted_hant_sources
        ]
        self.assertTrue(candidates)
        cross_owned_sources = {spec.source_offset for spec in MENU_LABELS if spec.status == "proven"}

        for entry in candidates:
            with self.subTest(key=entry.key):
                source = entry.source_text.encode("cp932") + b"\x00"
                self.assertEqual(
                    RAW[entry.source_offset:entry.source_offset + len(source)],
                    result[entry.source_offset:entry.source_offset + len(source)],
                )
                if entry.source_offset in cross_owned_sources:
                    # The command-label renderer owns this alias now; provenance stays pristine.
                    continue
                for pointer_offset in entry.pointer_offsets:
                    self.assertEqual(
                        RAW[pointer_offset:pointer_offset + 4],
                        result[pointer_offset:pointer_offset + 4],
                    )

    def test_composite_build_recenters_title_labels_and_preserves_packed_title_art(self) -> None:
        result = build_early_ui_elf(RAW)

        self.assertEqual(0x3C024210, struct.unpack_from("<I", result, 0x1ABF64)[0])
        self.assertEqual(0x3C0243AA, struct.unpack_from("<I", result, 0x1ABF84)[0])
        self.assertEqual(RAW[0x6989C0:0x6989C8], result[0x6989C0:0x6989C8])
        self.assertEqual(RAW[0x1AC600:0x1AC604], result[0x1AC600:0x1AC604])


    def test_composite_build_relocates_every_proven_menu_label_as_wide_text(self) -> None:
        result = build_early_ui_elf(RAW)
        _type, segment_file, segment_va, _paddr, segment_size, _memsz, _flags, _align = struct.unpack_from(
            "<IIIIIIII", result, 0x54
        )
        proven = [spec for spec in MENU_LABELS if spec.status == "proven"]
        self.assertEqual(18, len(proven))

        for spec in proven:
            with self.subTest(key=spec.key):
                self.assertEqual(
                    RAW[spec.source_offset:spec.source_offset + spec.capacity],
                    result[spec.source_offset:spec.source_offset + spec.capacity],
                )
                targets = {struct.unpack_from("<I", result, off)[0] for off in spec.pointer_offsets}
                self.assertEqual(1, len(targets))
                target_va = targets.pop()
                self.assertGreaterEqual(target_va, segment_va)
                self.assertLess(target_va, segment_va + segment_size)
                target_file = segment_file + target_va - segment_va
                assert spec.selected_english is not None
                expected = encode_ps2_english(spec.selected_english, collapse_spaces=False) + b"\x00"
                self.assertEqual(expected, result[target_file:target_file + len(expected)])

        media = next(spec for spec in MENU_LABELS if spec.key == "media")
        self.assertEqual(
            RAW[media.pointer_offsets[0]:media.pointer_offsets[0] + 4],
            result[media.pointer_offsets[0]:media.pointer_offsets[0] + 4],
        )

    def test_composite_build_includes_startup_pointer_relocation(self) -> None:
        result = build_early_ui_elf(RAW)
        target_va = struct.unpack_from("<I", result, NAME_PROMPT_POINTER_TABLE_OFFSET)[0]
        target = target_va - 0x00100000 + 0x80
        expected = encode_ps2_english("Enter last name.") + b"\x00"
        self.assertEqual(expected, result[target:target + len(expected)])
        self.assertGreaterEqual(target_va, 0x00100000)


    def test_composite_build_includes_horizontal_adv_layout(self) -> None:
        result = build_early_ui_elf(RAW)
        for offset, _expected, replacement in (*ADV_DG_LAYOUT_PATCHES, *ADV_SPEAKER_LAYOUT_PATCHES):
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

    def test_command_menu_source_slots_remain_pristine(self) -> None:
        result = build_early_ui_elf(RAW)
        for spec in MENU_LABELS:
            with self.subTest(key=spec.key):
                self.assertEqual(
                    RAW[spec.source_offset:spec.source_offset + spec.capacity],
                    result[spec.source_offset:spec.source_offset + spec.capacity],
                )

    def test_r29_preserves_every_frozen_hant_layout_owner(self) -> None:
        result = build_early_ui_elf(RAW)
        for offset, _expected, replacement in HANT_RUNTIME_LAYOUT_PATCHES:
            with self.subTest(offset=hex(offset)):
                self.assertEqual(replacement, struct.unpack_from("<I", result, offset)[0])



if __name__ == "__main__":
    unittest.main()
