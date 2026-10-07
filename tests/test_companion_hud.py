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
    COMPANION_ACTION_SLOT2_BUBBLE_HEIGHT_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_METADATA_VA,
    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_X_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_Y_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_PRISTINE_GEOMETRY,
    COMPANION_ACTION_SLOT2_BUBBLE_TABLE_RECORD_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_TARGET_GEOMETRY,
    COMPANION_ACTION_SLOT2_BUBBLE_WIDTH_OFFSET,
    COMPANION_ACTION_SLOT_RESOURCES,
    COMPANION_ACTION_SLOT_TEXT_X,
    COMPANION_ACTION_BUBBLE_METADATA_SIZE,
    COMPANION_GROUP2_NEXT_TABLE_POINTER_OFFSET,
    COMPANION_GROUP2_NEXT_TABLE_VA,
    COMPANION_GROUP2_RESOURCE_COUNT,
    COMPANION_GROUP2_TABLE_OFFSET,
    COMPANION_GROUP2_TABLE_POINTER_OFFSET,
    COMPANION_ACTION_ID_GETTER_VA,
    COMPANION_ACTION_ID_KEY,
    COMPANION_ACTION_ID_REFERENCE_PREIMAGES,
    COMPANION_ACTION_LABELS,
    COMPANION_ACTION_LAYOUTS,
    COMPANION_ACTION_LAYOUT_PATCHES,
    COMPANION_ACTION_RUNTIME_HOOK_SIZE,
    COMPANION_ACTION_RUNTIME_PREIMAGES,
    COMPANION_SLOT_INDEX_PREIMAGES,
    COMPANION_SLOT_POSITIONS,
    COMPANION_SLOT_POSITION_TABLE_OFFSET,
    COMPANION_COMMENT_EXTRA_POINTER_ALIASES,
    COMPANION_COMMENT_LINES,
    companion_comment_pointer_offsets,
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
        self.assertEqual(10, sum(len(offsets) for offsets in COMPANION_COMMENT_EXTRA_POINTER_ALIASES.values()))
        self.assertEqual(
            1794,
            sum(len(companion_comment_pointer_offsets(spec)) for spec in COMPANION_COMMENT_LINES),
        )
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

        extra_pointer = COMPANION_COMMENT_EXTRA_POINTER_ALIASES[0x3C46E8][0]
        tampered = bytearray(RAW)
        tampered[extra_pointer] ^= 1
        with self.assertRaisesRegex(ValueError, "companion comment pointer preimage mismatch"):
            validate_companion_hud_source(bytes(tampered))

    def test_r40_comment_alias_inventory_covers_every_direct_source_pointer(self) -> None:
        source_vas = {
            _ELF_MAIN_VADDR + spec.source_offset - _ELF_MAIN_FILE_OFFSET
            for spec in COMPANION_COMMENT_LINES
        }
        discovered = {
            offset
            for offset in range(0, len(RAW) - 3, 4)
            if struct.unpack_from("<I", RAW, offset)[0] in source_vas
        }
        owned = {
            pointer_offset
            for spec in COMPANION_COMMENT_LINES
            for pointer_offset in companion_comment_pointer_offsets(spec)
        }
        self.assertEqual(1794, len(discovered))
        self.assertEqual(discovered, owned)

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

        comments_by_source = {spec.source_offset: spec for spec in COMPANION_COMMENT_LINES}
        for source_offset, pointer_offsets in COMPANION_COMMENT_EXTRA_POINTER_ALIASES.items():
            spec = comments_by_source[source_offset]
            expected = encode_ps2_english(spec.display_english, collapse_spaces=False) + b"\x00"
            for pointer_offset in pointer_offsets:
                with self.subTest(extra_pointer_offset=hex(pointer_offset)):
                    target_va = struct.unpack_from("<I", result, pointer_offset)[0]
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
        # r40 restores the shared 0x68/0x69 metadata for passive/AFK chatter.
        # The accepted r35 compact geometry lives only in private action clones.
        bubble_offsets = (
            COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
            COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
            COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
            COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
        )
        self.assertEqual(
            COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY,
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

    def test_r38_runtime_selector_keeps_body_stable_and_points_tail_at_active_slot(self) -> None:
        result = build_early_ui_elf(RAW)
        _ptype, p_offset, p_vaddr, _paddr, p_filesz, _memsz, p_flags, _align = struct.unpack_from(
            "<IIIIIIII", result, 0x54
        )
        self.assertEqual(7, p_flags)

        # Keep the game's proven slot anchors.  r38 changes the bubble resource/
        # pivot, not the companion positions themselves.
        expected_slot_positions = tuple(
            component for position in COMPANION_SLOT_POSITIONS for component in position
        )
        self.assertEqual(
            expected_slot_positions,
            struct.unpack_from("<ffff", RAW, COMPANION_SLOT_POSITION_TABLE_OFFSET),
        )
        self.assertEqual(
            RAW[COMPANION_SLOT_POSITION_TABLE_OFFSET:COMPANION_SLOT_POSITION_TABLE_OFFSET + 16],
            result[COMPANION_SLOT_POSITION_TABLE_OFFSET:COMPANION_SLOT_POSITION_TABLE_OFFSET + 16],
        )
        for offset, expected in COMPANION_SLOT_INDEX_PREIMAGES:
            self.assertEqual(expected, struct.unpack_from("<I", result, offset)[0])

        jal = struct.unpack_from("<I", result, 0x66724)[0]
        self.assertEqual(0x03, jal >> 26)
        hook_va = (jal & 0x03FFFFFF) << 2
        self.assertGreaterEqual(hook_va, p_vaddr)
        self.assertLess(hook_va, p_vaddr + p_filesz)
        self.assertEqual(0x24040002, struct.unpack_from("<I", result, 0x66728)[0])

        hook_file = p_offset + hook_va - p_vaddr
        hook_words = struct.unpack_from(
            f"<{COMPANION_ACTION_RUNTIME_HOOK_SIZE // 4}I", result, hook_file
        )
        self.assertEqual(0x27BDFFF0, hook_words[0])
        self.assertEqual(0xAFBF000C, hook_words[1])
        self.assertEqual(0x34040000 | COMPANION_ACTION_ID_KEY, hook_words[2])
        self.assertEqual(
            0x0C000000 | ((COMPANION_ACTION_ID_GETTER_VA >> 2) & 0x03FFFFFF),
            hook_words[3],
        )
        self.assertEqual(0x3042FFFF, hook_words[5])
        self.assertEqual(0x38420000 | COMPANION_ACTION_ID_KEY, hook_words[6])
        self.assertEqual(0x2C43001F, hook_words[7])
        self.assertIn(0x860D02D0, hook_words)         # lh t5,0x2d0(s0): slot 0/1
        self.assertEqual(
            0x25A50000 | COMPANION_ACTION_SLOT_RESOURCES[0],
            hook_words[-6],
        )
        self.assertEqual(0x8FBF000C, hook_words[-5])
        self.assertEqual(0x27BD0010, hook_words[-4])
        self.assertEqual(0x24040002, hook_words[-3])
        self.assertEqual(0x03E00008, hook_words[-2])
        self.assertEqual(0, hook_words[-1])

        # r40 extends group 2 instead of mutating shared 0x68/0x69. The first
        # 164 records are byte-identical and private 0xA4/0xA5 point at compact
        # relocated clones, preserving the accepted r38 active-action geometry.
        self.assertEqual((0xA4, 0xA5), COMPANION_ACTION_SLOT_RESOURCES)
        resource_table_va = struct.unpack_from("<I", result, COMPANION_GROUP2_TABLE_POINTER_OFFSET)[0]
        self.assertNotEqual(COMPANION_GROUP2_NEXT_TABLE_VA, resource_table_va)
        self.assertEqual(
            COMPANION_GROUP2_NEXT_TABLE_VA,
            struct.unpack_from("<I", result, COMPANION_GROUP2_NEXT_TABLE_POINTER_OFFSET)[0],
        )
        resource_table_file = p_offset + resource_table_va - p_vaddr
        source_table = RAW[
            COMPANION_GROUP2_TABLE_OFFSET:
            COMPANION_GROUP2_TABLE_OFFSET + COMPANION_GROUP2_RESOURCE_COUNT * 8
        ]
        self.assertEqual(
            source_table,
            result[
                resource_table_file:
                resource_table_file + COMPANION_GROUP2_RESOURCE_COUNT * 8
            ],
        )
        private_geometries = (
            COMPANION_ACTION_BUBBLE_TARGET_GEOMETRY,
            COMPANION_ACTION_SLOT2_BUBBLE_TARGET_GEOMETRY,
        )
        for slot, (resource_id, expected_geometry) in enumerate(
            zip(COMPANION_ACTION_SLOT_RESOURCES, private_geometries, strict=True)
        ):
            metadata_va, record_count = struct.unpack_from(
                "<II", result, resource_table_file + resource_id * 8
            )
            self.assertEqual(1, record_count)
            metadata_file = p_offset + metadata_va - p_vaddr
            self.assertEqual(
                expected_geometry,
                struct.unpack_from("<ffff", result, metadata_file + 4),
            )
            if slot == 1:
                self.assertEqual(
                    COMPANION_ACTION_BUBBLE_METADATA_SIZE,
                    metadata_va - previous_metadata_va,
                )
            previous_metadata_va = metadata_va

        body_left = (
            COMPANION_SLOT_POSITIONS[0][0] - COMPANION_ACTION_BUBBLE_TARGET_GEOMETRY[2],
            COMPANION_SLOT_POSITIONS[1][0] - COMPANION_ACTION_SLOT2_BUBBLE_TARGET_GEOMETRY[2],
        )
        text_left = (
            COMPANION_SLOT_POSITIONS[0][0] + COMPANION_ACTION_SLOT_TEXT_X[0],
            COMPANION_SLOT_POSITIONS[1][0] + COMPANION_ACTION_SLOT_TEXT_X[1],
        )
        self.assertEqual(13.0, body_left[1] - body_left[0])
        self.assertEqual(13.0, text_left[1] - text_left[0])
        self.assertEqual(58.0, COMPANION_SLOT_POSITIONS[1][0] - COMPANION_SLOT_POSITIONS[0][0])

        # The original later action lookup remains byte-identical.
        for offset, expected in COMPANION_ACTION_ID_REFERENCE_PREIMAGES:
            self.assertEqual(expected, struct.unpack_from("<I", result, offset)[0])
        for offset, _expected, replacement in COMPANION_ACTION_LAYOUT_PATCHES:
            self.assertEqual(replacement, struct.unpack_from("<I", result, offset)[0])
        self.assertEqual(0x46000800, struct.unpack_from("<I", result, 0x66810)[0])
        self.assertEqual(0x46000800, struct.unpack_from("<I", result, 0x66828)[0])

    def test_r38_layout_patch_fails_closed_on_all_pristine_owners(self) -> None:
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

        tampered = bytearray(RAW)
        tampered[COMPANION_SLOT_POSITION_TABLE_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "companion slot position table drifted"):
            patch_companion_action_layout(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[COMPANION_GROUP2_TABLE_POINTER_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "companion group-2 table owner drifted"):
            patch_companion_action_layout(bytes(tampered))

        for offset, _expected in (*COMPANION_SLOT_INDEX_PREIMAGES, *COMPANION_ACTION_ID_REFERENCE_PREIMAGES):
            with self.subTest(slot_or_action_owner=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "companion slot/action-id owner drifted"):
                    patch_companion_action_layout(bytes(tampered))

        bubble_specs = (
            (
                COMPANION_ACTION_BUBBLE_TABLE_RECORD_OFFSET,
                COMPANION_ACTION_BUBBLE_METADATA_VA,
                (
                    COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
                    COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
                    COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
                    COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
                ),
                COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY,
            ),
            (
                COMPANION_ACTION_SLOT2_BUBBLE_TABLE_RECORD_OFFSET,
                COMPANION_ACTION_SLOT2_BUBBLE_METADATA_VA,
                (
                    COMPANION_ACTION_SLOT2_BUBBLE_WIDTH_OFFSET,
                    COMPANION_ACTION_SLOT2_BUBBLE_HEIGHT_OFFSET,
                    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_X_OFFSET,
                    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_Y_OFFSET,
                ),
                COMPANION_ACTION_SLOT2_BUBBLE_PRISTINE_GEOMETRY,
            ),
        )
        for record_offset, metadata_va, geometry_offsets, pristine_geometry in bubble_specs:
            self.assertEqual((metadata_va, 1), struct.unpack_from("<II", RAW, record_offset))
            self.assertEqual(
                pristine_geometry,
                tuple(struct.unpack_from("<f", RAW, offset)[0] for offset in geometry_offsets),
            )
            tampered = bytearray(RAW)
            tampered[record_offset] ^= 1
            with self.assertRaisesRegex(ValueError, "companion action bubble resource-table drifted"):
                patch_companion_action_layout(bytes(tampered))
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
