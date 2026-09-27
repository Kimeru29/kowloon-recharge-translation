from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.early_ui import build_early_ui_elf
from tools.adv_layout import ADV_SPEAKER_LAYOUT_PATCHES
from tools.startup_ui import NAME_PROMPT_LAYOUT_PATCHES
from tools.hant_ui import (
    HANT_ALL_HELP_TOPICS,
    HANT_CHROME_LABELS,
    HANT_CONFIG_LABELS,
    HANT_HELP_CATEGORY_LABELS,
    HANT_TUTORIAL_FONT_STYLE_OFFSET,
    HANT_TUTORIAL_ROW_SPACING_OFFSET,
)
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
        self.assertIn("hant_config_labels", names)
        self.assertIn("hant_help_category_labels", names)
        self.assertIn("adv_speaker_horizontal_layout", names)
        self.assertIn("hant_unresolved_pristine", names)
        self.assertIn("memory_card_1", names)
        self.assertIn("memory_card_1_boot_aliases", names)
        self.assertIn("name_flow_skip_reading", names)
        self.assertIn("name_prompt_centered_layout", names)
        self.assertIn("name_prompt_0", names)
        self.assertIn("name_prompt_2", names)
        self.assertIn("name_prompt_3", names)
        self.assertIn("runtime_name_Habaki", names)
        self.assertIn("title_english_label_geometry", names)
        self.assertIn("menu_semantic_fixed_labels", names)
        self.assertIn("menu_relocated_labels", names)
        self.assertIn("menu_unresolved_pristine", names)

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
        self.assertIn("hant_help_category_labels", failed_names)
        self.assertIn("name_prompt_0", failed_names)
        self.assertIn("name_flow_skip_reading", failed_names)
        self.assertIn("name_prompt_centered_layout", failed_names)
        self.assertIn("memory_card_1_boot_aliases", failed_names)
        self.assertIn("title_english_label_geometry", failed_names)
        self.assertIn("menu_semantic_fixed_labels", failed_names)
        self.assertIn("menu_relocated_labels", failed_names)
        self.assertNotIn("menu_unresolved_pristine", failed_names)

    def test_menu_acceptance_fails_closed_per_semantic_storage_class(self) -> None:
        translated = build_early_ui_elf(RAW)
        fixed = next(spec for spec in MENU_LABELS if spec.storage == "fixed-slot")
        relocated = next(spec for spec in MENU_LABELS if spec.storage == "relocated")
        unresolved = next(spec for spec in MENU_LABELS if spec.storage == "pristine")

        cases = (
            ("menu_semantic_fixed_labels", fixed.source_offset),
            ("menu_semantic_fixed_labels", fixed.pointer_offsets[0]),
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

    def test_hant_runtime_layout_acceptance_fails_closed_on_style_or_chrome_drift(self) -> None:
        translated = build_early_ui_elf(RAW)
        cases = (
            ("hant_tutorial_font_style", HANT_TUTORIAL_FONT_STYLE_OFFSET),
            ("hant_tutorial_row_spacing", HANT_TUTORIAL_ROW_SPACING_OFFSET),
            ("hant_chrome_labels", HANT_CHROME_LABELS[0].pointer_offset),
            ("hant_config_labels", HANT_CONFIG_LABELS[0].pointer_offset),
            ("hant_help_category_labels", HANT_HELP_CATEGORY_LABELS[0].pointer_offset),
            ("hant_help_topics", HANT_ALL_HELP_TOPICS[0].pointer_offset),
            ("hant_help_topics", HANT_ALL_HELP_TOPICS[-1].pointer_offset),
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
