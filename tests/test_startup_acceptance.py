from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.early_ui import build_early_ui_elf
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
        self.assertIn("memory_card_1", names)
        self.assertIn("memory_card_1_boot_aliases", names)
        self.assertIn("name_flow_skip_reading", names)
        self.assertIn("name_prompt_0", names)
        self.assertIn("name_prompt_2", names)
        self.assertIn("name_prompt_3", names)
        self.assertIn("runtime_name_Habaki", names)
        self.assertIn("title_english_backing_geometry", names)

    def test_pristine_elf_fails_translated_renderer_checks(self) -> None:
        checks = verify_startup_elf(RAW)
        failed_names = {check["name"] for check in checks if not check["ok"]}
        self.assertIn("adv_dg_horizontal_layout", failed_names)
        self.assertIn("translation_segment", failed_names)
        self.assertIn("hant_tutorial", failed_names)
        self.assertIn("name_prompt_0", failed_names)
        self.assertIn("name_flow_skip_reading", failed_names)
        self.assertIn("memory_card_1_boot_aliases", failed_names)
        self.assertIn("title_english_backing_geometry", failed_names)

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
        self.assertEqual(31, len(STARTUP_GRAPHICS_PATHS))
        self.assertEqual("BLBRD/B_GP019.BIN", STARTUP_GRAPHICS_PATHS[0])
        self.assertEqual("BLBRD/B_GP088.BIN", STARTUP_GRAPHICS_PATHS[1])
        self.assertEqual("BLBRD/INIT_MES/TR000.TMX", STARTUP_GRAPHICS_PATHS[2])
        self.assertEqual("BLBRD/INIT_MES/TR028.TMX", STARTUP_GRAPHICS_PATHS[-1])


if __name__ == "__main__":
    unittest.main()
