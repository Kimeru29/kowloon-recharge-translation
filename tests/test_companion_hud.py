from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.companion_hud import (
    COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
    COMPANION_ACTION_BUBBLE_METADATA_VA,
    COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
    COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
    COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY,
    COMPANION_ACTION_BUBBLE_TABLE_RECORD_OFFSET,
    COMPANION_ACTION_BUBBLE_TARGET_GEOMETRY,
    COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
    COMPANION_ACTION_LABELS,
    COMPANION_ACTION_LAYOUTS,
    COMPANION_ACTION_LAYOUT_PATCHES,
    COMPANION_ACTION_RUNTIME_PREIMAGES,
    COMPANION_COMMENT_LINES,
    encode_companion_action,
    patch_companion_action_layout,
    validate_companion_hud_source,
    wrap_companion_action_text,
)
from tools.dungeon_ui import DUNGEON_ACTION_LABELS, DUNGEON_ITEM_NAMES
from tools.early_ui import build_early_ui_elf
from tools.localization import encode_ps2_english


ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()
_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000


def _read_at_va(raw: bytes, va: int, size: int) -> bytes:
    _ptype, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _flags, _align = struct.unpack_from(
        "<IIIIIIII", raw, 0x54
    )
    relative = va - p_vaddr
    if 0 <= relative and relative + size <= p_filesz:
        return raw[p_offset + relative:p_offset + relative + size]
    main_offset = va - _ELF_MAIN_VADDR + _ELF_MAIN_FILE_OFFSET
    if 0 <= main_offset <= len(raw) - size:
        return raw[main_offset:main_offset + size]
    return b""


class CompanionHudTests(unittest.TestCase):
    def test_r30_comment_inventory_is_complete_ps4_exact_and_fail_closed(self) -> None:
        self.assertEqual(1650, len(COMPANION_COMMENT_LINES))
        self.assertEqual(1784, sum(len(spec.pointer_offsets) for spec in COMPANION_COMMENT_LINES))
        self.assertEqual(7, sum(spec.official_english == "@D" for spec in COMPANION_COMMENT_LINES))
        self.assertEqual(1650, len({spec.source_offset for spec in COMPANION_COMMENT_LINES}))
        first = COMPANION_COMMENT_LINES[0]
        self.assertEqual(0x3C19A0, first.source_offset)
        self.assertEqual("千年以上の昔、地震で水没した", first.source_text)
        self.assertEqual("Heracleion flooded after an", first.official_english)
        self.assertEqual((0x3D3328,), first.pointer_offsets)
        validate_companion_hud_source(RAW)

        tampered = bytearray(RAW)
        tampered[first.pointer_offsets[0]] ^= 1
        with self.assertRaisesRegex(ValueError, "companion comment pointer preimage mismatch"):
            validate_companion_hud_source(bytes(tampered))

    def test_r30_companion_action_inventory_covers_hud_skill_labels(self) -> None:
        self.assertEqual(31, len(COMPANION_ACTION_LABELS))
        throw_rock = COMPANION_ACTION_LABELS[25]
        self.assertEqual(0x3F8D84, throw_rock.pointer_offset)
        self.assertEqual("石を投げる", throw_rock.source_text)
        self.assertEqual("Throw a Rock", throw_rock.english)
        self.assertEqual("official_exact", throw_rock.provenance)
        self.assertEqual(26, sum(spec.provenance == "official_exact" for spec in COMPANION_ACTION_LABELS))

    def test_r30_build_relocates_companion_comments_and_current_hud_action(self) -> None:
        result = build_early_ui_elf(RAW)
        cases = (
            (0x3D3328, "Heracleion flooded after an"),
            (0x3D332C, "earthquake 1,000 years ago."),
            (0x3F8D84, "Throw a Rock"),
        )
        for pointer_offset, english in cases:
            with self.subTest(pointer_offset=hex(pointer_offset)):
                target_va = struct.unpack_from("<I", result, pointer_offset)[0]
                expected = encode_ps2_english(english, collapse_spaces=False) + b"\x00"
                self.assertEqual(expected, _read_at_va(result, target_va, len(expected)))

        for spec in (COMPANION_COMMENT_LINES[0], COMPANION_ACTION_LABELS[25]):
            source = spec.source_text.encode("cp932") + b"\x00"
            self.assertEqual(source, result[spec.source_offset:spec.source_offset + len(source)])

    def test_r36_companion_actions_wrap_generically_and_preserve_r35_short_layout(self) -> None:
        self.assertEqual(("Throw a Rock",), wrap_companion_action_text("Throw a Rock"))
        self.assertEqual(
            ("Smoking an Aroma", "Stick"),
            wrap_companion_action_text("Smoking an Aroma Stick"),
        )
        self.assertEqual(
            ("Secret Technique:", "Reverse Waterfall", "Blade"),
            wrap_companion_action_text("Secret Technique: Reverse Waterfall Blade"),
        )

        self.assertEqual((48.0, 45.0, -99.0), (
            COMPANION_ACTION_LAYOUTS[25].height,
            COMPANION_ACTION_LAYOUTS[25].pivot_y,
            COMPANION_ACTION_LAYOUTS[25].text_y,
        ))
        self.assertEqual((64.0, 61.0, -115.0), (
            COMPANION_ACTION_LAYOUTS[2].height,
            COMPANION_ACTION_LAYOUTS[2].pivot_y,
            COMPANION_ACTION_LAYOUTS[2].text_y,
        ))
        self.assertEqual((80.0, 77.0, -131.0), (
            COMPANION_ACTION_LAYOUTS[24].height,
            COMPANION_ACTION_LAYOUTS[24].pivot_y,
            COMPANION_ACTION_LAYOUTS[24].text_y,
        ))
        self.assertTrue(all(len(line) <= 17 for layout in COMPANION_ACTION_LAYOUTS for line in layout.lines))

        result = build_early_ui_elf(RAW)
        # The accepted one-line startup/default geometry remains exactly r35.
        bubble_offsets = (
            COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
            COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
            COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
            COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
        )
        self.assertEqual(
            COMPANION_ACTION_BUBBLE_TARGET_GEOMETRY,
            tuple(struct.unpack_from("<f", result, offset)[0] for offset in bubble_offsets),
        )

        # Every owned action is encoded by the same wrapper. Long official PS4
        # labels receive literal 0x0A line breaks; short labels remain unchanged.
        for action_id in (2, 24, 25):
            spec = COMPANION_ACTION_LABELS[action_id]
            target_va = struct.unpack_from("<I", result, spec.pointer_offset)[0]
            expected = encode_companion_action(spec.english)
            self.assertEqual(expected, _read_at_va(result, target_va, len(expected)))
        self.assertIn(b"\x0a", encode_companion_action(COMPANION_ACTION_LABELS[2].english))
        self.assertEqual(2, encode_companion_action(COMPANION_ACTION_LABELS[24].english).count(b"\x0a"))
        self.assertNotIn(b"\x0a", encode_companion_action(COMPANION_ACTION_LABELS[25].english))

    def test_r36_runtime_selector_is_installed_in_executable_translation_segment(self) -> None:
        result = build_early_ui_elf(RAW)
        _ptype, p_offset, p_vaddr, _paddr, p_filesz, _memsz, p_flags, _align = struct.unpack_from(
            "<IIIIIIII", result, 0x54
        )
        self.assertEqual(7, p_flags)

        jal = struct.unpack_from("<I", result, 0x66724)[0]
        self.assertEqual(0x03, jal >> 26)
        hook_va = (jal & 0x03FFFFFF) << 2
        self.assertGreaterEqual(hook_va, p_vaddr)
        self.assertLess(hook_va, p_vaddr + p_filesz)
        self.assertEqual(0x24040002, struct.unpack_from("<I", result, 0x66728)[0])

        hook_file = p_offset + hook_va - p_vaddr
        hook_words = struct.unpack_from("<24I", result, hook_file)
        self.assertEqual(0x860202D0, hook_words[0])  # lh v0,0x2d0(s0)
        self.assertEqual(0x2C43001F, hook_words[1])  # bounds-check 31 action ids
        self.assertEqual(0x24050068, hook_words[-3]) # proven down-tail bubble
        self.assertEqual(0x03E00008, hook_words[-2]) # jr ra
        self.assertEqual(0, hook_words[-1])

        # Static owners that do not depend on action id stay frozen.
        for offset, _expected, replacement in COMPANION_ACTION_LAYOUT_PATCHES:
            self.assertEqual(replacement, struct.unpack_from("<I", result, offset)[0])
        self.assertEqual(0x46000800, struct.unpack_from("<I", result, 0x66828)[0])

    def test_r36_layout_patch_fails_closed_on_all_pristine_owners(self) -> None:
        for offset, _expected, _replacement in COMPANION_ACTION_LAYOUT_PATCHES:
            with self.subTest(static_offset=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "companion action layout preimage mismatch"):
                    patch_companion_action_layout(bytes(tampered))

        for offset, _expected in COMPANION_ACTION_RUNTIME_PREIMAGES:
            with self.subTest(runtime_offset=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "companion action runtime preimage mismatch"):
                    patch_companion_action_layout(bytes(tampered))

        geometry_offsets = (
            COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
            COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
            COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
            COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
        )
        self.assertEqual(
            COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY,
            tuple(struct.unpack_from("<f", RAW, offset)[0] for offset in geometry_offsets),
        )
        for offset in geometry_offsets:
            with self.subTest(metadata_offset=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "companion action bubble geometry drifted"):
                    patch_companion_action_layout(bytes(tampered))

    def test_r30_keeps_accepted_r29_dungeon_owners_frozen(self) -> None:
        result = build_early_ui_elf(RAW)
        for spec in DUNGEON_ACTION_LABELS:
            ref = spec.code_reference
            self.assertNotEqual(ref.expected_lui, struct.unpack_from("<I", result, ref.lui_offset)[0])
        for spec in DUNGEON_ITEM_NAMES:
            with self.subTest(item_id=spec.item_id):
                self.assertNotEqual(
                    _ELF_MAIN_VADDR + spec.source_offset - _ELF_MAIN_FILE_OFFSET,
                    struct.unpack_from("<I", result, spec.pointer_offset)[0],
                )


if __name__ == "__main__":
    unittest.main()
