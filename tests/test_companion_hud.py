from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.companion_hud import (
    COMPANION_ACTION_LABELS,
    COMPANION_ACTION_LAYOUT_PATCHES,
    COMPANION_COMMENT_LINES,
    patch_companion_action_layout,
    validate_companion_hud_source,
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

    def test_r32_companion_action_callout_matches_accepted_ps4_style_alignment(self) -> None:
        result = build_early_ui_elf(RAW)

        # r31 proved the 12px English font and vertical clearance. Runtime then
        # showed that the fixed 160x32 bubble's visible body/spike sat slightly
        # to the right of the caption. r32 shifts only the backing 8px left and
        # freezes the accepted text/font/Y owners.
        expected_words = {
            0x666F0: 0x3C024080,  # backing X: anchor + 4px (r31 was +12)
            0x66708: 0x3C02C274,  # backing Y: anchor - 61px
            0x66804: 0x3C0241A0,  # text X: anchor + 20px
            0x6681C: 0x3C02C258,  # text Y: anchor - 54px
            0x6686C: 0x24050001,  # style 1 = 12x12
        }
        for offset, expected in expected_words.items():
            with self.subTest(offset=hex(offset)):
                self.assertEqual(expected, struct.unpack_from("<I", result, offset)[0])

        # Group-2 index 0x18 remains the proven fixed 160x32 bubble resource.
        self.assertEqual(160.0, struct.unpack_from("<f", result, 0x34EAD4)[0])
        self.assertEqual(32.0, struct.unpack_from("<f", result, 0x34EAD8)[0])

    def test_r32_layout_patch_fails_closed_on_each_pristine_owner(self) -> None:
        for offset, _expected, _replacement in COMPANION_ACTION_LAYOUT_PATCHES:
            with self.subTest(offset=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "companion action layout preimage mismatch"):
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
