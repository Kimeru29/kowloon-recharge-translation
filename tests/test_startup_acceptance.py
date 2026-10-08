from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.early_ui import build_early_ui_elf
from tools.adv_layout import ADV_SPEAKER_LAYOUT_PATCHES
from tools.startup_ui import NAME_CONFIRMATION_FOCUS_PATCHES, NAME_PROMPT_LAYOUT_PATCHES
from tools.title_layout import TITLE_LABEL_BACKING_PATCHES
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
    HANT_RINGTONES,
    HANT_HELP_CATEGORY_LABELS,
    HANT_RUNTIME_LAYOUT_PATCHES,
    HANT_TUTORIAL_FONT_STYLE_OFFSET,
    HANT_TUTORIAL_SINGLETON_STYLE_OFFSET,
    HANT_TUTORIAL_ROW_SPACING_OFFSET,
)
from tools.companion_hud import (
    COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
    COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
    COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
    COMPANION_ACTION_BUBBLE_TABLE_RECORD_OFFSET,
    COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
    COMPANION_ACTION_ID_REFERENCE_PREIMAGES,
    COMPANION_ACTION_LABELS,
    COMPANION_ACTION_LAYOUT_PATCHES,
    COMPANION_ACTION_RUNTIME_PATCH_OFFSETS,
    COMPANION_ACTION_VISIBILITY_PATCH_OFFSETS,
    COMPANION_AFK_ALPHA_PREIMAGES,
    COMPANION_AFK_RUNTIME_PATCH_OFFSETS,
    COMPANION_AFK_PANEL_LAYOUT_PATCH_OFFSETS,
    COMPANION_AFK_PANEL_VALIDATION_OFFSETS,
    COMPANION_AFK_TABLE_OFFSET,
    COMPANION_SLOT_INDEX_PREIMAGES,
    COMPANION_SLOT_POSITION_TABLE_OFFSET,
    COMPANION_COMMENT_LINES,
)
from tools.dungeon_ui import DUNGEON_ACTION_LABELS, DUNGEON_ITEM_NAMES
from tools.menu_ui import MENU_LABELS
from tools.startup_acceptance import STARTUP_GRAPHICS_PATHS, verify_startup_elf

ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


class StartupAcceptanceTests(unittest.TestCase):
    def test_translated_elf_passes_all_renderer_class_checks(self) -> None:
        translated = build_early_ui_elf(RAW)
        checks = verify_startup_elf(translated)
        failures = [check for check in checks if not check["ok"]]
        self.assertEqual([], failures)
        names = {check["name"] for check in checks}
        self.assertIn("adv_dg_horizontal_layout", names)
        self.assertIn("translation_segment", names)
        self.assertIn("runtime_heap_break", names)
        self.assertIn("hant_tutorial", names)
        self.assertIn("hant_inventory_proven_targets", names)
        self.assertIn("hant_wrapped_layout_payload", names)
        self.assertIn("hant_tutorial_font_style", names)
        self.assertIn("hant_tutorial_row_spacing", names)
        self.assertIn("hant_chrome_labels", names)
        self.assertIn("hant_help_topics", names)
        self.assertIn("hant_help_bodies", names)
        self.assertIn("hant_help_body_metadata", names)
        self.assertIn("hant_runtime_layout", names)
        self.assertIn("hant_mail_chrome", names)
        self.assertIn("hant_dictionary_definitions", names)
        self.assertIn("hant_content_values", names)
        self.assertIn("hant_ringtones", names)
        self.assertIn("hant_dictionary_tabs", names)
        self.assertIn("hant_dictionary_terms", names)
        self.assertIn("hant_config_labels", names)
        self.assertIn("hant_help_category_labels", names)
        self.assertIn("adv_speaker_horizontal_layout", names)
        self.assertIn("hant_unresolved_pristine", names)
        self.assertIn("memory_card_1", names)
        self.assertIn("memory_card_1_boot_aliases", names)
        self.assertIn("name_flow_skip_reading", names)
        self.assertIn("name_prompt_centered_layout", names)
        self.assertIn("name_confirmation_focus_layout", names)
        self.assertIn("name_prompt_0", names)
        self.assertIn("name_prompt_2", names)
        self.assertIn("name_prompt_3", names)
        self.assertIn("runtime_name_Habaki", names)
        self.assertIn("title_english_label_geometry", names)
        self.assertIn("menu_relocated_labels", names)
        self.assertIn("menu_unresolved_pristine", names)
        self.assertIn("dungeon_action_labels", names)
        self.assertIn("dungeon_item_names", names)
        self.assertIn("companion_hud_comments", names)
        self.assertIn("companion_hud_actions", names)
        self.assertIn("companion_afk_free_talk", names)
        self.assertIn("companion_hud_layout", names)

    def test_pristine_elf_fails_translated_renderer_checks(self) -> None:
        checks = verify_startup_elf(RAW)
        failed_names = {check["name"] for check in checks if not check["ok"]}
        self.assertIn("adv_dg_horizontal_layout", failed_names)
        self.assertIn("translation_segment", failed_names)
        self.assertIn("hant_tutorial", failed_names)
        self.assertIn("hant_inventory_proven_targets", failed_names)
        self.assertIn("hant_wrapped_layout_payload", failed_names)
        self.assertIn("hant_tutorial_font_style", failed_names)
        self.assertIn("hant_chrome_labels", failed_names)
        self.assertIn("hant_config_labels", failed_names)
        self.assertIn("hant_help_body_metadata", failed_names)
        self.assertIn("hant_runtime_layout", failed_names)
        self.assertIn("hant_mail_chrome", failed_names)
        self.assertIn("hant_dictionary_definitions", failed_names)
        self.assertIn("hant_content_values", failed_names)
        self.assertIn("hant_ringtones", failed_names)
        self.assertIn("hant_dictionary_tabs", failed_names)
        self.assertIn("hant_dictionary_terms", failed_names)
        self.assertIn("hant_help_category_labels", failed_names)
        self.assertIn("name_prompt_0", failed_names)
        self.assertIn("name_flow_skip_reading", failed_names)
        self.assertIn("name_prompt_centered_layout", failed_names)
        self.assertIn("name_confirmation_focus_layout", failed_names)
        self.assertIn("memory_card_1_boot_aliases", failed_names)
        self.assertIn("title_english_label_geometry", failed_names)
        self.assertIn("menu_relocated_labels", failed_names)
        self.assertNotIn("menu_unresolved_pristine", failed_names)
        self.assertIn("dungeon_action_labels", failed_names)
        self.assertIn("dungeon_item_names", failed_names)
        self.assertIn("companion_hud_comments", failed_names)
        self.assertIn("companion_hud_actions", failed_names)
        self.assertIn("companion_afk_free_talk", failed_names)
        self.assertIn("companion_hud_layout", failed_names)

    def test_menu_acceptance_fails_closed_per_semantic_storage_class(self) -> None:
        translated = build_early_ui_elf(RAW)
        relocated = next(spec for spec in MENU_LABELS if spec.storage == "relocated")
        unresolved = next(spec for spec in MENU_LABELS if spec.storage == "pristine")

        cases = (
            ("menu_relocated_labels", relocated.source_offset),
            ("menu_relocated_labels", relocated.pointer_offsets[0]),
            ("menu_unresolved_pristine", unresolved.source_offset),
            ("menu_unresolved_pristine", unresolved.pointer_offsets[0]),
        )
        for name, offset in cases:
            with self.subTest(name=name, offset=f"{offset:#x}"):
                tampered = bytearray(translated)
                tampered[offset] ^= 1
                check = next(check for check in verify_startup_elf(bytes(tampered)) if check["name"] == name)
                self.assertFalse(check["ok"])

    def test_dungeon_ui_acceptance_fails_closed_on_each_owner_class(self) -> None:
        translated = build_early_ui_elf(RAW)
        action = DUNGEON_ACTION_LABELS[0]
        item = DUNGEON_ITEM_NAMES[0]
        cases = (
            ("dungeon_action_labels", action.source_offset),
            ("dungeon_action_labels", action.code_reference.lui_offset),
            ("dungeon_action_labels", action.code_reference.addiu_offset),
            ("dungeon_item_names", item.source_offset),
            ("dungeon_item_names", item.pointer_offset),
        )
        for name, offset in cases:
            with self.subTest(name=name, offset=hex(offset)):
                tampered = bytearray(translated)
                tampered[offset] ^= 1
                check = next(check for check in verify_startup_elf(bytes(tampered)) if check["name"] == name)
                self.assertFalse(check["ok"])

    def test_companion_hud_acceptance_fails_closed_on_comment_and_action_owners(self) -> None:
        translated = build_early_ui_elf(RAW)
        comment = COMPANION_COMMENT_LINES[0]
        action = COMPANION_ACTION_LABELS[25]
        cases = (
            ("companion_hud_comments", comment.source_offset),
            ("companion_hud_comments", comment.pointer_offsets[0]),
            ("companion_hud_actions", action.source_offset),
            ("companion_hud_actions", action.pointer_offset),
        )
        for name, offset in cases:
            with self.subTest(name=name, offset=hex(offset)):
                tampered = bytearray(translated)
                tampered[offset] ^= 1
                check = next(check for check in verify_startup_elf(bytes(tampered)) if check["name"] == name)
                self.assertFalse(check["ok"])

    def test_companion_afk_acceptance_fails_closed_on_structural_pointer_owner(self) -> None:
        translated = build_early_ui_elf(RAW)
        tampered = bytearray(translated)
        tampered[COMPANION_AFK_TABLE_OFFSET + 8] ^= 1
        check = next(
            check
            for check in verify_startup_elf(bytes(tampered))
            if check["name"] == "companion_afk_free_talk"
        )
        self.assertFalse(check["ok"])

    def test_companion_hud_layout_acceptance_fails_closed_on_each_owner(self) -> None:
        translated = build_early_ui_elf(RAW)
        offsets = [offset for offset, _expected, _replacement in COMPANION_ACTION_LAYOUT_PATCHES]
        offsets.extend(COMPANION_ACTION_RUNTIME_PATCH_OFFSETS)
        offsets.extend(COMPANION_ACTION_VISIBILITY_PATCH_OFFSETS)
        offsets.extend(offset for offset, _expected in COMPANION_AFK_ALPHA_PREIMAGES)
        offsets.extend(COMPANION_AFK_RUNTIME_PATCH_OFFSETS)
        offsets.extend(COMPANION_AFK_PANEL_LAYOUT_PATCH_OFFSETS)
        offsets.extend(COMPANION_AFK_PANEL_VALIDATION_OFFSETS)
        offsets.extend(offset for offset, _expected in COMPANION_SLOT_INDEX_PREIMAGES)
        offsets.extend(offset for offset, _expected in COMPANION_ACTION_ID_REFERENCE_PREIMAGES)
        offsets.extend(
            (
                COMPANION_SLOT_POSITION_TABLE_OFFSET,
                COMPANION_ACTION_BUBBLE_TABLE_RECORD_OFFSET,
                COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
                COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
                COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
                COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
            )
        )
        for offset in offsets:
            with self.subTest(offset=hex(offset)):
                tampered = bytearray(translated)
                tampered[offset] ^= 1
                check = next(
                    check for check in verify_startup_elf(bytes(tampered))
                    if check["name"] == "companion_hud_layout"
                )
                self.assertFalse(check["ok"])

    def test_r50_companion_wrap_and_panel_payloads_fail_closed(self) -> None:
        translated = build_early_ui_elf(RAW)
        _ptype, p_offset, p_vaddr, _paddr, _p_filesz, _memsz, _flags, _align = struct.unpack_from(
            "<IIIIIIII", translated, 0x54
        )

        geometry_jal = struct.unpack_from("<I", translated, 0x66050)[0]
        text_jal = struct.unpack_from("<I", translated, 0x66284)[0]
        geometry_va = (geometry_jal & 0x03FFFFFF) << 2
        text_va = (text_jal & 0x03FFFFFF) << 2
        geometry_file = p_offset + geometry_va - p_vaddr
        text_file = p_offset + text_va - p_vaddr

        geometry_words = struct.unpack_from("<46I", translated, geometry_file)
        hi = geometry_words[10] & 0xFFFF
        lo = geometry_words[11] & 0xFFFF
        if lo & 0x8000:
            lo -= 0x10000
        table_va = ((hi << 16) + lo) & 0xFFFFFFFF
        table_file = p_offset + table_va - p_vaddr

        for owner, offset in (
            ("geometry_hook", geometry_file),
            ("text_hook", text_file),
            ("layout_table", table_file),
        ):
            with self.subTest(owner=owner):
                tampered = bytearray(translated)
                tampered[offset] ^= 1
                check = next(
                    check for check in verify_startup_elf(bytes(tampered))
                    if check["name"] == "companion_hud_layout"
                )
                self.assertFalse(check["ok"])

    def test_hant_runtime_layout_acceptance_fails_closed_on_style_or_chrome_drift(self) -> None:
        translated = build_early_ui_elf(RAW)
        cases = (
            ("hant_tutorial_font_style", HANT_TUTORIAL_FONT_STYLE_OFFSET),
            ("hant_tutorial_font_style", HANT_TUTORIAL_SINGLETON_STYLE_OFFSET),
            ("hant_tutorial_row_spacing", HANT_TUTORIAL_ROW_SPACING_OFFSET),
            ("hant_chrome_labels", HANT_CHROME_LABELS[0].pointer_offset),
            ("hant_config_labels", HANT_CONFIG_LABELS[0].pointer_offset),
            ("hant_help_category_labels", HANT_HELP_CATEGORY_LABELS[0].pointer_offset),
            ("hant_help_topics", HANT_ALL_HELP_TOPICS[0].pointer_offset),
            ("hant_help_topics", HANT_ALL_HELP_TOPICS[-1].pointer_offset),
            ("hant_help_bodies", HANT_HELP_BODIES[0].descriptor_offset),
            ("hant_help_body_metadata", HANT_HELP_BODIES[0].metadata_descriptor_offset),
            *(("hant_runtime_layout", offset) for offset, _expected, _replacement in HANT_RUNTIME_LAYOUT_PATCHES),
            ("hant_mail_chrome", HANT_MAIL_COUNT_LABEL.lui_offset),
            ("hant_dictionary_definitions", HANT_DICTIONARY_DEFINITIONS[0].descriptor_offset),
            ("hant_content_values", HANT_CONTENT_LABELS[0].pointer_offsets[0]),
            ("hant_ringtones", HANT_RINGTONES[0].pointer_offsets[0]),
            ("hant_dictionary_tabs", HANT_DICTIONARY_TABS[0].pointer_offsets[0]),
            ("hant_dictionary_terms", HANT_DICTIONARY_TERMS[0].pointer_offsets[0]),
            ("hant_dictionary_terms", HANT_DICTIONARY_TERMS[-1].pointer_offsets[0]),
        )
        for name, offset in cases:
            with self.subTest(name=name):
                tampered = bytearray(translated)
                tampered[offset] ^= 1
                check = next(check for check in verify_startup_elf(bytes(tampered)) if check["name"] == name)
                self.assertFalse(check["ok"])


    def test_name_prompt_centering_acceptance_fails_closed_on_each_owner(self) -> None:
        translated = build_early_ui_elf(RAW)
        for offset, _expected, _replacement in NAME_PROMPT_LAYOUT_PATCHES:
            with self.subTest(offset=hex(offset)):
                tampered = bytearray(translated)
                tampered[offset] ^= 1
                check = next(
                    check for check in verify_startup_elf(bytes(tampered))
                    if check["name"] == "name_prompt_centered_layout"
                )
                self.assertFalse(check["ok"])

    def test_name_confirmation_focus_acceptance_fails_closed_on_each_owner(self) -> None:
        translated = build_early_ui_elf(RAW)
        for offset, _expected, _replacement in NAME_CONFIRMATION_FOCUS_PATCHES:
            with self.subTest(offset=hex(offset)):
                tampered = bytearray(translated)
                tampered[offset] ^= 1
                check = next(
                    check for check in verify_startup_elf(bytes(tampered))
                    if check["name"] == "name_confirmation_focus_layout"
                )
                self.assertFalse(check["ok"])

    def test_title_backing_acceptance_fails_closed_on_each_resource_or_position_owner(self) -> None:
        translated = build_early_ui_elf(RAW)
        for offset, _expected, _replacement in TITLE_LABEL_BACKING_PATCHES:
            with self.subTest(offset=hex(offset)):
                tampered = bytearray(translated)
                tampered[offset] ^= 1
                check = next(
                    check for check in verify_startup_elf(bytes(tampered))
                    if check["name"] == "title_english_label_geometry"
                )
                self.assertFalse(check["ok"])

    def test_adv_speaker_acceptance_fails_closed_on_orientation_drift(self) -> None:
        translated = build_early_ui_elf(RAW)
        offset = ADV_SPEAKER_LAYOUT_PATCHES[0][0]
        tampered = bytearray(translated)
        tampered[offset] ^= 1
        check = next(
            check for check in verify_startup_elf(bytes(tampered))
            if check["name"] == "adv_speaker_horizontal_layout"
        )
        self.assertFalse(check["ok"])

    def test_v10_adv_patch_does_not_satisfy_v11_dg_layout_acceptance(self) -> None:
        old = bytearray(RAW)
        for offset, replacement in (
            (0x14FA60, 0x80430465),
            (0x14FA68, 0x00031843),
            (0x14FAA4, 0x80440463),
            (0x14FAA8, 0x0080182D),
        ):
            struct.pack_into("<I", old, offset, replacement)

        check = next(
            check for check in verify_startup_elf(bytes(old))
            if check["name"] == "adv_dg_horizontal_layout"
        )
        self.assertFalse(check["ok"])

    def test_startup_graphics_manifest_is_complete_and_stable(self) -> None:
        self.assertEqual(32, len(STARTUP_GRAPHICS_PATHS))
        self.assertEqual("BLBRD/B_GP019.BIN", STARTUP_GRAPHICS_PATHS[0])
        self.assertEqual("BLBRD/B_GP020.BIN", STARTUP_GRAPHICS_PATHS[1])
        self.assertEqual("BLBRD/B_GP088.BIN", STARTUP_GRAPHICS_PATHS[2])
        self.assertEqual("BLBRD/INIT_MES/TR000.TMX", STARTUP_GRAPHICS_PATHS[3])
        self.assertEqual("BLBRD/INIT_MES/TR028.TMX", STARTUP_GRAPHICS_PATHS[-1])


if __name__ == "__main__":
    unittest.main()
